import cv2
import numpy as np

INTERNAL = 0
EXTERNAL = 4

print("initializing...")
cap = cv2.VideoCapture(INTERNAL, cv2.CAP_V4L2)
print(f"done. ({cap})")

# Load the cascade
face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
eye_cascade = cv2.CascadeClassifier("haarcascade_eye.xml")


def prep_img(img):
    img = cv2.GaussianBlur(img, (5, 5), 0)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img


def find_movement(img1, img2):
    diff = cv2.absdiff(prep_img(img1), prep_img(img2))
    _, thresh = cv2.threshold(diff, 10, 255, cv2.THRESH_BINARY)
    return thresh


def gray_to_hsv(hue):
    imgsize = np.shape(hue)
    allblack = np.zeros((imgsize[0], imgsize[1]), dtype=np.uint8)
    sat = allblack
    sat.fill(255)
    val = allblack
    val.fill(255)
    hsv = cv2.merge([hue, sat, val])

    rgb = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    return rgb


ret, img = cap.read()
imgsize = np.shape(img)
img_cum_movement = np.zeros((imgsize[0], imgsize[1]), dtype=np.uint8)

history_len = 100
move_hist = [img_cum_movement for i in range(history_len)]
move_idx = 0

allblack = np.zeros((imgsize[0], imgsize[1]), dtype=np.uint8)


while True:
    old_img = img
    move_idx = (move_idx + 1) % history_len
    # Capture frame-by-frame
    ret, img = cap.read()
    if ret is False:
        print("Error, can't read from camera. Exitting.")
        quit()

    # find the cascade

    img_diff = find_movement(img, old_img)
    move_hist[move_idx] = img_diff

    img_movement = allblack

    # Go through the history of images, and combine them
    #  with a weight double the number of images
    #  -> if a change appeared on half of the images, it'll be full white
    #  This will amplify the movement visibility
    for i in range(move_idx, move_idx + history_len):
        i %= history_len
        img_movement = cv2.addWeighted(
            img_movement, 1, move_hist[i], 1 / history_len * 2, 0
        )

    img_dst = cv2.addWeighted(
        gray_to_hsv(img_movement),
        0.6,
        img,
        0.4,
        0,
    )

    cv2.imshow("Difference", img_dst)
    #    cv2.imshow("HSV", cv2.cvtColor(img_dst, cv2.COLOR_BGR2HSV_FULL))

    inpkey = cv2.waitKey(1) & 0xFF
    if inpkey == ord("q"):
        break


# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()
