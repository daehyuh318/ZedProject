import os
import pyzed.sl as sl
import cv2
import numpy as np
import threading
from datetime import datetime
import sys
from queue import Queue
from numpy import inf

zed = sl.Camera()
runtime = sl.InitParameters()  # 객체 생성

runtime.camera_resolution = sl.RESOLUTION.HD2K
# runtime.camera_resolution = sl.RESOLUTION.HD2K  # Use HD1080 video mode
runtime.camera_fps = 15  # Set fps at 60
runtime.coordinate_units = sl.UNIT.METER
runtime.depth_minimum_distance = 0.15
runtime.depth_maximum_distance = 40
runtime.depth_mode = sl.DEPTH_MODE.ULTRA  # depth 해상도 ULTRA
sensors_data = sl.SensorsData()
que = Queue()

status = False  # 키 입력 확인
save_path = 'saved_img'  # 저장 경로
frm_path = ''  # 저장 날짜
count = 0  # 저장 파일 카운트


def DepthNormalizing(data):
    max_data, min_data = np.max(data), np.min(data)
    data = (data - min_data) / (max_data - min_data) * 255
    return data


def distance_undefined(nd_array):
    nd_array[nd_array == inf] = 0
    nd_array[nd_array == -inf] = 0
    np.nan_to_num(nd_array)
    return nd_array


def file_writer():
    global que
    while True:
        if not que.empty():
            que_dict = que.get()
            for key, value in que_dict.items():
                if key == "dis" or key == "slope":
                    np.save(value[0], value[1])
                else:
                    cv2.imwrite(value[0], value[1])


def record():
    global que, count, zed, runtime, status

    # Mat
    left = sl.Mat()
    right = sl.Mat()
    depth = sl.Mat()
    dis = sl.Mat()

    while True:
        if status:
            if zed.grab(runtime) == sl.ERROR_CODE.SUCCESS:
                zed.retrieve_image(left, sl.VIEW.LEFT)  # images
                zed.retrieve_image(right, sl.VIEW.RIGHT)
                zed.retrieve_image(depth, sl.VIEW.DEPTH)
                zed.retrieve_measure(dis, sl.MEASURE.DEPTH)  # distance
                path = os.path.join(save_path, frm_path)
                zed.get_sensors_data(sensors_data, sl.TIME_REFERENCE.CURRENT)
                quaternion = sensors_data.get_imu_data().get_pose().get_orientation().get()

                # Save image
                que.put({'left': [os.path.join(path, f'left_{str(count).zfill(4)}.jpg'), left.get_data()]})
                que.put({'right': [os.path.join(path, f'right_{str(count).zfill(4)}.jpg'), right.get_data()]})
                que.put({'depth': [os.path.join(path, f'depth_{str(count).zfill(4)}.jpg'), depth.get_data()]})
                que.put({'dis': [os.path.join(path, f'distance_{str(count).zfill(4)}.npy'),
                                 DepthNormalizing(distance_undefined(dis.get_data()))]})
                que.put({'slope': [os.path.join(path, f'slope_{str(count).zfill(4)}.npy'), quaternion]})
                count += 1
        else:
            count = 0


def main():
    global count, zed, runtime, status, frm_path
    err = zed.open(runtime)
    if err != sl.ERROR_CODE.SUCCESS:
        print('카메라가 연결되어있지 않던가 이미 카메라가 켜져있습니다')
        exit()
    else:
        print('카메라 연결성공!')

    runtime = sl.RuntimeParameters()
    runtime.sensing_mode = sl.SENSING_MODE.FILL

    left = sl.Mat()
    # right = sl.Mat()
    # depth = sl.Mat()
    # Get image
    image_size = zed.get_camera_information().camera_resolution
    # image resizing
    image_size.width = image_size.width / 2.5
    image_size.height = image_size.height / 2.5

    print("\n스페이스바: 촬영을 시작/종료\nESC : 프로그램종료\n")
    while True:

        if zed.grab(runtime) == sl.ERROR_CODE.SUCCESS:

            # Show Camera
            zed.retrieve_image(left, sl.VIEW.LEFT)
            # zed.retrieve_image(right, sl.VIEW.RIGHT)
            # zed.retrieve_image(depth, sl.VIEW.DEPTH)

            resized_left = cv2.resize(left.get_data(), (image_size.width, image_size.height))
            # resized_right = cv2.resize(right.get_data(), (image_size.width, image_size.height))
            # resized_depth = cv2.resize(depth.get_data(), (image_size.width, image_size.height))

            cv2.putText(resized_left, str(count), (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 255), 3)
            # cv2.putText(resized_left, 'Zed Left', (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 255), 3)
            # cv2.putText(resized_right, 'Zed Right', (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 255), 3)
            cv2.imshow('ZED_left', resized_left)
            # cv2.imshow('ZED_right', resized_right)
            # cv2.imshow('ZED_depth', resized_depth)

        else:
            cv2.destroyAllWindows()
            zed.close()
            break

        key = cv2.waitKey(5)  # Ese to exit program Key Event
        if key == 27:
            break
        elif key == 32:  # Space bar to save Image Key Event
            status = not status
            if status:
                frm_path = datetime.today().strftime('%Y%m%d_%H%M%S%f')
                root_path = os.path.join(save_path, frm_path)
                os.makedirs(root_path, exist_ok=True)  # image dir
                os.makedirs(root_path + "/video", exist_ok=True)  # video dir
                print(f"녹화시작 {root_path}에 파일이 저장됩니다.")
            else:
                # print(root_path)
                # os.system(
                #     "ffmpeg -f image2 -r 5 -i " + root_path + "/depth_%04d.jpg -vcodec mpeg4 -y " + root_path + "/video/depth_images_convert_video.mp4")
                print(f"{count}개의 파일이 {root_path}에 저장되었습니다.")
                print("\n스페이스바를 눌러 촬영을 시작/종료 하세요\nESC : 프로그램종료\n")
                count = 0
                frm_path = ''

    cv2.destroyAllWindows()
    zed.close()
    sys.exit(0)


if __name__ == "__main__":
    que_thread = threading.Thread(target=file_writer, args=(), daemon=True)
    que_thread.start()
    record_Thread = threading.Thread(target=record, args=(), daemon=True)
    record_Thread.start()
    main()
    record_Thread.join()
    que_thread.join()
