#!/usr/bin/env python3
"""
批量去除图片左上角"AI 生成"水印 - 优化版
使用多尺度修复和颜色混合，覆盖原文件
"""

import os
import cv2
import numpy as np
from pathlib import Path

def detect_watermark_region(img):
    """
    检测水印区域
    水印特征：左上角，半透明白色文字"AI 生成"
    """
    height, width = img.shape[:2]

    # 定义水印区域 - 根据实际图片调整
    # 通常水印在左上角 15% 宽度，8% 高度范围内
    roi_y1, roi_y2 = int(height * 0.01), int(height * 0.12)
    roi_x1, roi_x2 = int(width * 0.01), int(width * 0.18)

    return (roi_x1, roi_y1, roi_x2, roi_y2)

def smart_inpaint(img, mask):
    """
    智能修复 - 结合多种算法
    """
    # 方法 1: TELEA 算法
    result1 = cv2.inpaint(img, mask, 5, cv2.INPAINT_TELEA)

    # 方法 2: NS 算法 (Navier-Stokes)
    result2 = cv2.inpaint(img, mask, 5, cv2.INPAINT_NS)

    # 混合两种结果
    blended = cv2.addWeighted(result1, 0.6, result2, 0.4, 0)

    return blended

def remove_watermark_advanced(image_path):
    """
    高级水印去除 - 直接覆盖原文件
    """
    # 读取图片
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"  无法读取图片：{image_path}")
        return False

    height, width = img.shape[:2]

    # 获取水印区域
    x1, y1, x2, y2 = detect_watermark_region(img)

    # 创建精细掩码 - 只覆盖文字区域
    mask = np.zeros((height, width), dtype=np.uint8)

    # 使用自适应阈值检测文字区域
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 裁剪出 ROI 区域
    roi = gray[y1:y2, x1:x2]

    # 自适应阈值检测亮色文字
    thresh = cv2.adaptiveThreshold(
        roi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 11, 2
    )

    # 形态学操作，连接文字
    kernel = np.ones((3,3), np.uint8)
    dilated_thresh = cv2.dilate(thresh, kernel, iterations=2)
    eroded_thresh = cv2.erode(dilated_thresh, kernel, iterations=1)

    # 将检测到的文字区域映射回原掩码
    mask[y1:y2, x1:x2] = eroded_thresh

    # 如果没检测到文字，使用默认矩形区域
    if cv2.countNonZero(mask) < 100:
        mask = np.zeros((height, width), dtype=np.uint8)
        # 根据图片尺寸调整掩码大小
        mask_w = max(60, int(width * 0.12))
        mask_h = max(25, int(height * 0.08))
        mask[0:mask_h, 0:mask_w] = 255

    # 对掩码进行轻微膨胀，确保完全覆盖水印
    kernel = np.ones((5,5), np.uint8)
    mask = cv2.dilate(mask, kernel, iterations=2)

    # 智能修复
    result = smart_inpaint(img, mask)

    # 保存覆盖原文件
    cv2.imwrite(str(image_path), result)
    return True

def process_folder(folder_path):
    """
    批量处理文件夹中的所有图片 - 直接覆盖
    """
    folder = Path(folder_path)

    # 支持的图片格式
    image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}

    # 收集所有图片（排除已处理的）
    image_files = []
    for ext in image_extensions:
        for img in folder.rglob(f'*{ext}'):
            if 'no_watermark' not in str(img.name):
                image_files.append(img)
        for img in folder.rglob(f'*{ext.upper()}'):
            if 'no_watermark' not in str(img.name):
                image_files.append(img)

    # 删除之前生成的 no_watermark 文件
    for old_file in folder.rglob('no_watermark_*'):
        try:
            old_file.unlink()
            print(f"删除旧文件：{old_file.name}")
        except:
            pass

    print(f"\n找到 {len(image_files)} 张图片待处理")
    print("-" * 50)

    success_count = 0
    for img_path in image_files:
        print(f"处理：{img_path.name}")

        if remove_watermark_advanced(img_path):
            success_count += 1
            print(f"  ✓ 完成")
        else:
            print(f"  ✗ 失败")

    print("-" * 50)
    print(f"处理完成！成功：{success_count}/{len(image_files)}")

if __name__ == "__main__":
    base_folder = Path.home() / "Desktop" / "电商设计图片"
    process_folder(base_folder)
