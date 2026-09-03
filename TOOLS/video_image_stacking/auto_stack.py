import os
import cv2
import numpy as np
from time import time



# Align and stack images with ECC method
# Slower but more accurate
def stackImagesECC(file_list, blend='mean'):
    M = np.eye(3, 3, dtype=np.float32)

    first_image = None
    aligned_images = []

    for file in file_list:
        image = cv2.imread(file,1).astype(np.float32) / 255
        print(file)
        if first_image is None:
            # convert to gray scale floating point image
            first_image = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
            aligned_images.append(image)
        else:
            # Estimate perspective transform
            s, M = cv2.findTransformECC(cv2.cvtColor(image,cv2.COLOR_BGR2GRAY), first_image, M, cv2.MOTION_HOMOGRAPHY)
            w, h, _ = image.shape
            # Align image to first image
            image = cv2.warpPerspective(image, M, (h, w))
            aligned_images.append(image)

    stack = np.stack(aligned_images, axis=0)
    # median rejects ghosting from local/non-rigid motion that a single global
    # homography can't correct (mean bakes misaligned pixels straight in)
    stacked_image = np.median(stack, axis=0) if blend == 'median' else np.mean(stack, axis=0)
    stacked_image = (stacked_image*255).astype(np.uint8)
    return stacked_image


# Align and stack images with dense optical flow (per-pixel correspondence)
# Unlike ECC/ORB (one global homography for the whole frame), this finds a
# separate motion vector for every pixel, so it can correct local/non-rigid
# motion (fur, ears, breathing) that a single transform can't touch.
def stackImagesOpticalFlow(file_list, blend='median'):
    use_dis = hasattr(cv2, 'DISOpticalFlow_create')
    flow_engine = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM) if use_dis else None

    first_gray = None
    aligned_images = []
    grid_x = grid_y = None

    for file in file_list:
        print(file)
        image = cv2.imread(file, 1)
        imageF = image.astype(np.float32) / 255
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        if first_gray is None:
            first_gray = gray
            h, w = gray.shape
            grid_x, grid_y = np.meshgrid(np.arange(w), np.arange(h))
            aligned_images.append(imageF)
        else:
            # flow(y,x) = displacement from reference pixel (y,x) to where that
            # same scene point sits in this frame
            if use_dis:
                flow = flow_engine.calc(first_gray, gray, None)
            else:
                flow = cv2.calcOpticalFlowFarneback(first_gray, gray, None, 0.5, 3, 21, 5, 5, 1.2, 0)
            map_x = (grid_x + flow[..., 0]).astype(np.float32)
            map_y = (grid_y + flow[..., 1]).astype(np.float32)
            warped = cv2.remap(imageF, map_x, map_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            aligned_images.append(warped)

    stack = np.stack(aligned_images, axis=0)
    stacked_image = np.median(stack, axis=0) if blend == 'median' else np.mean(stack, axis=0)
    stacked_image = (stacked_image * 255).astype(np.uint8)
    return stacked_image


# Align and stack images by matching ORB keypoints
# Faster but less accurate
def stackImagesKeypointMatching(file_list):

    orb = cv2.ORB_create()

    # disable OpenCL to because of bug in ORB in OpenCV 3.1
    cv2.ocl.setUseOpenCL(False)

    stacked_image = None
    first_image = None
    first_kp = None
    first_des = None
    for file in file_list:
        print(file)
        image = cv2.imread(file,1)
        imageF = image.astype(np.float32) / 255

        # compute the descriptors with ORB
        kp = orb.detect(image, None)
        kp, des = orb.compute(image, kp)

        # create BFMatcher object
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

        if first_image is None:
            # Save keypoints for first image
            stacked_image = imageF
            first_image = image
            first_kp = kp
            first_des = des
        else:
             # Find matches and sort them in the order of their distance
            matches = matcher.match(first_des, des)
            matches = sorted(matches, key=lambda x: x.distance)

            src_pts = np.float32(
                [first_kp[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
            dst_pts = np.float32(
                [kp[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)

            # Estimate perspective transformation
            M, mask = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, 5.0)
            w, h, _ = imageF.shape
            imageF = cv2.warpPerspective(imageF, M, (h, w))
            stacked_image += imageF

    stacked_image /= len(file_list)
    stacked_image = (stacked_image*255).astype(np.uint8)
    return stacked_image

# ===== MAIN =====
# Read all files in directory
import argparse


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('input_dir', help='Input directory of images ()')
    parser.add_argument('output_image', help='Output image name')
    parser.add_argument('--method', help='Stacking method ORB (faster), ECC (more precise, global), or FLOW (dense optical flow, corrects local/non-rigid motion)')
    parser.add_argument('--blend', choices=['mean', 'median'], default='mean', help='mean (default, original behavior) or median (rejects ghosting from local motion)')
    parser.add_argument('--show', help='Show result image',action='store_true')
    args = parser.parse_args()

    image_folder = args.input_dir
    if not os.path.exists(image_folder):
        print("ERROR {} not found!".format(image_folder))
        exit()

    file_list = sorted(os.listdir(image_folder))
    file_list = [os.path.join(image_folder, x)
                 for x in file_list if x.endswith(('.jpg', '.png','.bmp'))]

    if args.method is not None:
        method = str(args.method)
    else:
        method = 'KP'

    tic = time()

    if method == 'ECC':
        # Stack images using ECC method
        description = "Stacking images using ECC method"
        print(description)
        stacked_image = stackImagesECC(file_list, blend=args.blend)

    elif method == 'ORB':
        #Stack images using ORB keypoint method
        description = "Stacking images using ORB method"
        print(description)
        stacked_image = stackImagesKeypointMatching(file_list)

    elif method == 'FLOW':
        description = "Stacking images using dense optical flow method"
        print(description)
        stacked_image = stackImagesOpticalFlow(file_list, blend=args.blend)

    else:
        print("ERROR: method {} not found!".format(method))
        exit()

    print("Stacked {0} in {1} seconds".format(len(file_list), (time()-tic) ))

    print("Saved {}".format(args.output_image))
    cv2.imwrite(str(args.output_image),stacked_image)

    # Show image
    if args.show:
        cv2.imshow(description, stacked_image)
        cv2.waitKey(0)
