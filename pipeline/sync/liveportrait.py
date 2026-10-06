"""LivePortrait (Guo et al. 2024) run from its ONNX export, for DOT's mouths (relip.py).

LivePortrait splits a face into appearance features and implicit 3D keypoints (head pose, scale and expression), and a
warping generator redraws the face from any set of keypoints. Two uses here:

  transfer: another frame of the same take, whose mouth says what the voice does, moved into this frame's head pose
            (its expression keypoints on this frame's pose), so its drawn mouth lands where this frame's is;
  lips:     this frame's own lips opened or closed, by the lip retargeting module, which takes the keypoints and a pair
            of lip ratios (the lips' gap over the mouth's width, as they are and as wanted) and returns the offsets.

The takes are anime drawings; the motion extractor reads them well enough for both. Output crops are 512 px.

Models: the ONNX export of LivePortrait in facefusion's model assets, downloaded from its GitHub release on first use.
"""
import os
import urllib.request

import cv2
import numpy as np
import onnxruntime as ort
from scipy.spatial.transform import Rotation

MODELS = os.environ.get('LIVEPORTRAIT_DIR', '/tmp/work/lp')
URL = 'https://github.com/facefusion/facefusion-assets/releases/download/models-3.0.0/live_portrait_{}.onnx'
PARTS = ['feature_extractor', 'motion_extractor', 'lip_retargeter', 'stitcher', 'generator']
# FFHQ 512 alignment template (eyes, nose tip, mouth corners), as facefusion aligns faces for LivePortrait
FFHQ512 = np.array([[0.37691676, 0.46864664], [0.62285697, 0.46912813], [0.50123859, 0.61331904],
                    [0.39308822, 0.72541100], [0.61150205, 0.72490465]], np.float32)

_S = {}


def sessions():
    if not _S:
        os.makedirs(MODELS, exist_ok=True)
        so = ort.SessionOptions()
        so.intra_op_num_threads = int(os.environ.get('LIVEPORTRAIT_THREADS', '4'))
        for p in PARTS:
            f = os.path.join(MODELS, f'live_portrait_{p}.onnx')
            if not os.path.exists(f):
                print('downloading', os.path.basename(f), flush=True)
                urllib.request.urlretrieve(URL.format(p), f + '.part')
                os.replace(f + '.part', f)
            _S[p] = ort.InferenceSession(f, so, providers=['CPUExecutionProvider'])
    return _S


def crop_face(frame, lm5, scale=1.5, size=512):
    """Similarity-align the face (5 points) to the FFHQ template; scale > 1 leaves more room around the face."""
    lm = np.array(lm5, np.float32)
    lm = (lm - lm[2]) * scale + lm[2]
    M = cv2.estimateAffinePartial2D(lm, FFHQ512 * size, method=cv2.RANSAC, ransacReprojThreshold=100)[0]
    crop = cv2.warpAffine(frame, M, (size, size), borderMode=cv2.BORDER_REPLICATE, flags=cv2.INTER_AREA)
    return crop, M


class Face:
    """A face crop's appearance features and implicit keypoints, with the pose they decompose into."""

    def __init__(self, crop):
        S = sessions()
        x = cv2.resize(crop, (256, 256), interpolation=cv2.INTER_AREA)[:, :, ::-1] / 255.0
        x = np.expand_dims(x.transpose(2, 0, 1), 0).astype(np.float32)
        self.fv = S['feature_extractor'].run(None, {'input': x})[0]
        p, y, r, self.sc, self.tr, self.ex, self.mp = S['motion_extractor'].run(None, {'input': x})
        self.R = Rotation.from_euler('xyz', [p, y, r], degrees=True).as_matrix().astype(np.float32)
        self.kp = (self.sc * (self.mp @ self.R.T + self.ex) + self.tr).astype(np.float32)


def lip_offsets(kp, ratio_now, ratio_wanted):
    """Keypoint offsets that move the lips' gap/width ratio from ratio_now to ratio_wanted."""
    inp = np.concatenate([kp.reshape(1, -1), np.array([[ratio_now, ratio_wanted]], np.float32)], 1).astype(np.float32)
    return sessions()['lip_retargeter'].run(None, {'input': inp})[0]


def draw(source, kp, frame_kp):
    """`source`'s face redrawn with its keypoints moved to kp, stitched to sit in the frame whose own keypoints are
    frame_kp (512 px, BGR)."""
    S = sessions()
    kp = S['stitcher'].run(None, {'source': kp.astype(np.float32), 'target': frame_kp})[0]
    out = S['generator'].run(None, {'feature_volume': source.fv, 'source': kp, 'target': source.kp})[0][0]
    return (out.transpose(1, 2, 0).clip(0, 1) * 255).astype(np.uint8)[:, :, ::-1]


def lips(face, ratio_now, ratio_wanted):
    """The face with its own lips opened or closed: ratio_now -> ratio_wanted."""
    return draw(face, face.kp + lip_offsets(face.kp, ratio_now, ratio_wanted), face.kp)


def transfer(body, donor, ratio_now=None, ratio_wanted=None):
    """The donor's face (its own drawn mouth) moved to the body's head pose, so its mouth lands where the body's is;
    optionally with the lips then opened or closed a little further."""
    kp = (body.sc * (donor.mp @ body.R.T + donor.ex) + body.tr).astype(np.float32)
    if ratio_now is not None and abs(ratio_wanted - ratio_now) > 1e-3:
        kp = kp + lip_offsets(kp, ratio_now, ratio_wanted)
    return draw(donor, kp, body.kp)
