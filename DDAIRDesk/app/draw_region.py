# -*- coding: utf-8 -*-
"""
@Copyright
@FileName   : draw_region.py
@Author     : MJJ
@Version    :
@Date       : 12/12/2023 7:23 PM
@Description:
@Update     :
@Software   : PyCharm
"""
import cv2

# 四边形点的列表
points = []

def draw_polygon(image, points):
    """ 绘制多边形 """
    for i, point in enumerate(points):
        cv2.circle(image, point, 3, (0, 0, 255), -1, cv2.LINE_AA)
        if i > 0:
            cv2.line(image, points[i - 1], point, (0, 255, 0), 2, cv2.LINE_AA)

    if len(points) == 4:
        cv2.line(image, points[3], points[0], (0, 255, 0), 2, cv2.LINE_AA)

def click_event(event, x, y, flags, params):
    # 鼠标左键点击事件
    if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
        points.append((x, y))
        draw_polygon(img, points)
        cv2.imshow('image', img)

# 主程序
def main():
    global img
    cap = cv2.VideoCapture(0)

    cv2.namedWindow('image',cv2.WINDOW_NORMAL)
    cv2.setMouseCallback('image', click_event)

    while True:
        ret, img = cap.read()
        if not ret:
            break
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        print(img.shape)

        if points:
            draw_polygon(img, points)

        cv2.imshow('image', img)

        # 按 'q' 退出
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    # 保存点位到文本文件
    if len(points) == 4:
        with open('points.txt', 'w') as file:
            for point in points:
                file.write(f'({point[0]}, {point[1]}),')

if __name__ == "__main__":
    main()
