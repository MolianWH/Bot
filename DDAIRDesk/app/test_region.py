# -*- coding: utf-8 -*-
"""
@Copyright
@FileName   : test_region.py
@Author     : MJJ
@Version    :
@Date       : 12/12/2023 7:32 PM 
@Description: 
@Update     :
@Software   : PyCharm
"""
import matplotlib.path as mpltPath

# 定义四边形的顶点
polygon = [(157, 161), (486, 134), (505, 325), (32, 348)]

# 创建路径
path = mpltPath.Path(polygon)

# 待判断的点
point = (300, 200)  # 示例点

# 判断点是否在多边形内
inside = path.contains_point(point)

print("Point", point, "is inside the polygon?" , inside)