# -*- coding: utf-8 -*-
# @Copyright
# @FileName   : DDFaceRecognition.py
# @Author     : HYD
# @Version    :
# @Date       : 2023/7/28 10:12
# @Description: 可列出参考连接，如mediapipe的demo连接； 模块功能等
# @Update     :
# @Software   : PyCharm


import os
import time
import math

import loguru
import numpy as np
import insightface
import cv2
from PIL import ImageFont, ImageDraw, Image
from sklearn import preprocessing
from DDAIRDesk.tools.read_yaml import read_yaml
from DDAIRDesk.plugins.DDBasePlugin import DDBasePlugin


def draw_txt(img, msg, point):
    b, g, r, a = 0, 255, 0, 0
    # 设置字体大小
    fontpath = "simsun.ttc"
    font = ImageFont.truetype(fontpath, 15)
    # 将numpy array的图片格式转为PIL的图片格式
    img_pil = Image.fromarray(img)
    # 创建画板
    draw = ImageDraw.Draw(img_pil)
    # 在图片上绘制中文
    draw.text(point, msg, font=font, fill=(b, g, r, a))
    # 将图片转为numpy array的数据格式
    return np.array(img_pil)


class DDFaceRecognition(DDBasePlugin):
    def __init__(self, yaml_path):
        """

        Args:
            yaml_path: 配置文件路径
        """
        super(DDFaceRecognition, self).__init__()
        # 加载人脸识别模型
        try:
            self.config = read_yaml(yaml_path, 'DDFaceRecognition')
            self.threshold = self.config.get('threshold', 1.0)
            self.face_db = self.config.get('face_db', './face_db')
            self.gpu_id = self.config.get('gpu_id', 0)
        except FileNotFoundError as e:
            print("配置文件不存在:", e)
            exit()
        except KeyError as e:
            print(f"配置文件中DDFaceRecognition出错!({e})")
            exit()

    def load_model(self):
        self.model = insightface.app.FaceAnalysis(providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
        self.model.prepare(ctx_id=self.gpu_id)
        # 人脸库的人脸特征
        self.faces_embedding = list()
        # 加载人脸库中的人脸
        self.__load_faces(self.face_db)

    # 加载人脸库中的人脸
    def __load_faces(self, face_db_path):
        """

        Args: 注册过的人脸数据加载
            face_db_path: 注册的人脸图片路劲

        Returns:

        """
        if not os.path.exists(face_db_path):
            os.makedirs(face_db_path)
        for root, dirs, files in os.walk(face_db_path):
            for file in files:
                input_image = cv2.imdecode(np.fromfile(os.path.join(root, file), dtype=np.uint8), 1)
                group = os.path.split(root)[1]
                user_data = file.split(".")[0]
                user_id = user_data.split("_")[0]
                user_name = user_data.replace(user_id + '_', "", 1)
                try:
                    face = self.model.get(input_image)[0]
                except Exception as e:
                    loguru.logger.info(f"用户：{user_name}注册失败!{e}")
                    continue
                embedding = np.array(face.embedding).reshape((1, -1))
                embedding = preprocessing.normalize(embedding)
                self.faces_embedding.append({
                    "user_id": user_id,
                    "user_name": user_name,
                    "feature": embedding,
                    "group": group
                })

    def __call__(self, img, output_img=False):
        """人脸识别

        Args:
            img: 输入图片
            output_img: 是否输出图片

        Returns:检测框和user_id和user_name
        """
        image = img.copy()
        faces = self.model.get(image)
        results = list()
        for face in faces:
            result = dict()
            # 获取人脸属性
            result["bbox"] = np.array(face.bbox).astype(np.int32).tolist()
            # result["landmark"] = np.array(face.landmark_2d_106).astype(np.int32).tolist()
            result["age"] = face.age
            result['gender'] = '女' if face.gender == 0 else '男'
            # 开始人脸识别
            embedding = np.array(face.embedding).reshape((1, -1))
            embedding = preprocessing.normalize(embedding)
            result["user_id"] = ""
            result["user_name"] = ""
            result['group'] = ''
            closest_face = self.__find_closest_face(embedding)
            if closest_face:
                result["user_id"] = closest_face["user_id"]
                result["user_name"] = closest_face["user_name"]
                result['group'] = closest_face["group"]
            results.append(result)
            if output_img:
                box = result['bbox']
                user_name = result['user_name']
                cv2.rectangle(image, (box[0], box[1]), (box[2], box[3]), (0, 0, 255), thickness=2)
                image = draw_txt(image, user_name, (box[0], box[1]))
        if output_img:
            DDBasePlugin.DDPluginDataFlow['DDFaceDetectionYolov5'] = {'res': results, 'out_img': image}
            return {'res': results, 'out_img': image}
        DDBasePlugin.DDPluginDataFlow['DDFaceDetectionYolov5'] = {'res': results}
        return {'res': results}

    def __find_closest_face(self, target_feature):
        """找到最像的特征脸

        Args:
            target_feature: 目标特征脸

        Returns:
            最小距离对应的人脸特征。如果不存在，返回None

        """
        min_dist = float("inf")   # 初始化为无穷大
        closest_face = None
        for com_face in self.faces_embedding:
            diff = np.subtract(target_feature, com_face["feature"])
            dist = np.sqrt(np.sum(np.square(diff)))
            if dist < min_dist:
                min_dist = dist
                closest_face = com_face

        if min_dist < self.threshold:
            return closest_face
        else:
            return None
    @staticmethod
    def __feature_compare(feature1, feature2, threshold):
        """欧式距离

        Args:
            feature1: 人脸特征
            feature2: 人脸特征
            threshold: 欧式距离阈值

        Returns: 是否是同一人

        """
        diff = np.subtract(feature1, feature2)
        dist = np.sum(np.square(diff), 1)
        if dist < threshold:
            return True
        else:
            return False

    def register(self, image, name):
        """
        人脸注册
        Args:
            image: 输入图片
            name: 用户名

        Returns:
            注册成功返回用户ID， 用户名；注册失败返回None

        """
        faces = self.model.get(image)
        if len(faces) != 1:
            return None
        # 判断人脸是否存在
        embedding = np.array(faces[0].embedding).reshape((1, -1))
        embedding = preprocessing.normalize(embedding)
        is_exits = False
        for com_face in self.faces_embedding:
            r = self.__feature_compare(embedding, com_face["feature"], self.threshold)
            if r:
                is_exits = True
        if is_exits:  # 如果库中存在人脸，则不再注册。
            return None
        user_id = str(math.floor(time.time()))
        image_name = f"{user_id}_{name}.png"
        # 符合注册条件保存图片，同时把特征添加到人脸特征库中
        cv2.imencode('.png', image)[1].tofile(os.path.join(self.face_db, image_name))
        self.faces_embedding.append({
            "user_id": user_id,
            "user_name": name,
            "feature": embedding,
            "group": "default"
        })
        return user_id, name

    def __del__(self):
        self.model = None
        print("DDFaceRecognition closed!")


def get_plugin_class():
    """获取插件类

    Returns:插件

    """
    return DDFaceRecognition

