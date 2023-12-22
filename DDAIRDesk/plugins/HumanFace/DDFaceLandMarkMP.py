# -*- coding: utf-8 -*-
# @Copyright
# @FileName   : DDFaceLandMarkMP.py
# @Author     : MJJ
# @Version    : 0.X.23XXXX
# @Date       : 7/14/2023
# @Description: mediapipe计算人脸关键点
# @Upadate    : 
# @Software   : PyCharm
import cv2
import numpy as np
import mediapipe as mdp

from DDAIRDesk.tools.read_yaml import read_yaml
from DDAIRDesk.plugins.DDBasePlugin import DDBasePlugin

class DDFaceLandMark(DDBasePlugin):
    """mediapipe人脸478关键点检测
    注意修改了DDAIRDesk插件，可自定义绘制颜色

    """

    def __init__(self, yaml_path):

        super(DDFaceLandMark, self).__init__()
        try:
            self.config = read_yaml(yaml_path, 'DDFaceLandMarkMediaPipe')
            self.max_num_faces = self.config['max_num_faces']
            self.refine_landmarks = self.config['refine_landmarks']
            self.detection_threshold = self.config['detection_threshold']
            self.tracking_threshold = self.config['tracking_threshold']
            self.draw_color = tuple(self.config['draw_color'])
            self.draw_thickness = self.config['draw_thickness']
        except FileNotFoundError as e:
            print("配置文件不存在:", e)
            exit()
        except KeyError as e:
            print(f"配置文件中DDFaceLandMarkMediaPipe出错!({e})")
            exit()

        # mediapipe
        self.mp_face_mesh = mdp.solutions.face_mesh
        self.mediapipe_drawing = mdp.solutions.drawing_utils
        self.mediapipe_drawing_styles = self.mediapipe_drawing.DrawingSpec(color=self.draw_color, thickness=self.draw_thickness)
        self.mediapipe_infer = self.mp_face_mesh.FaceMesh(max_num_faces=self.max_num_faces,
                                                          refine_landmarks=self.refine_landmarks,
                                                          min_detection_confidence=self.detection_threshold,
                                                          min_tracking_confidence=self.tracking_threshold)

    def __call__(self, img, output_img=False):
        """

        Args:
            img: 输入图片
            output_img: 是否输出图片

        Returns:检测框

        """
        img_cpy = img.copy()
        results = self.mediapipe_infer.process(cv2.cvtColor(img_cpy, cv2.COLOR_BGR2RGB))
        face_landmarks = None
        if results.multi_face_landmarks:
            face_landmarks = results.multi_face_landmarks[0]
            # for face_landmarks in results.multi_face_landmarks:
            #     # convert to NUMPY ARRAY data format(暂时保留）
            #     landmarks_np = np.array(
            #         [(lm.x, lm.y, lm.z) for lm in face_landmarks.landmark]
            #     )
        if output_img:
            img_res = self.vis(img_cpy, face_landmarks)
            return {'res': face_landmarks, 'out_img': img_res}
        return {'res': face_landmarks}

    def vis(self, image: np.ndarray, landmark):
        '''展示mediapipe结果

        Args:
            image: 输入图像
            landmark: mediapipe输出的landmarks
            windows_name: 显示的窗口名
            show_mesh: 是否绘制mesh
            hide_image: 是否隐藏原图像

        Returns:

        '''
        self.mediapipe_drawing.draw_landmarks(
            image=image,
            landmark_list=landmark,
            connections=self.mp_face_mesh.FACEMESH_TESSELATION,
            landmark_drawing_spec=None,
            connection_drawing_spec=self.mediapipe_drawing_styles)
        self.mediapipe_drawing.draw_landmarks(
            image=image,
            landmark_list=landmark,
            connections=self.mp_face_mesh.FACEMESH_CONTOURS,
            landmark_drawing_spec=None,
            connection_drawing_spec=self.mediapipe_drawing_styles)
        self.mediapipe_drawing.draw_landmarks(
            image=image,
            landmark_list=landmark,
            connections=self.mp_face_mesh.FACEMESH_IRISES,
            landmark_drawing_spec=None,
            connection_drawing_spec=self.mediapipe_drawing_styles)
        return cv2.flip(image, 1)

    def __del__(self):
        self.mediapipe_infer = None
        print("DDFaceLandMarkMediaPipe closed!")


def get_plugin_class():
    """获取插件类

    Returns:插件

    """
    return DDFaceLandMark
