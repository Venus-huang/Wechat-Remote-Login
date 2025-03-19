from flask import Flask, jsonify
from flask_cors import CORS
import pyautogui
import win32gui
import win32con
import cv2
import numpy as np
import os
from PIL import ImageGrab

app = Flask(__name__)
CORS(app)

class WeChatLoginHelper:
    def __init__(self):
        # 存储按钮模板图片的目录
        self.template_dir = "templates"
        self.login_button_template = os.path.join(self.template_dir, "login_button.png")
        
        # 确保模板目录存在
        if not os.path.exists(self.template_dir):
            os.makedirs(self.template_dir)

    def find_wechat_window(self):
        """查找微信窗口"""
        def callback(hwnd, hwnds):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if "微信" in title:
                    hwnds.append(hwnd)
            return True
        
        hwnds = []
        win32gui.EnumWindows(callback, hwnds)
        return hwnds[0] if hwnds else None

    def capture_screen(self):
        """捕获屏幕截图"""
        screenshot = ImageGrab.grab()
        screenshot_np = np.array(screenshot)
        return cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)

    def find_button_position(self, screen_img, template_path, threshold=0.8):
        """
        在屏幕截图中查找按钮位置
        :param screen_img: 屏幕截图（numpy数组）
        :param template_path: 模板图片路径
        :param threshold: 匹配阈值
        :return: (x, y) 按钮中心坐标，如果未找到则返回None
        """
        if not os.path.exists(template_path):
            print(f"模板图片不存在: {template_path}")
            return None

        # 读取模板图片
        template = cv2.imread(template_path)
        if template is None:
            print("无法读取模板图片")
            return None

        # 模板匹配
        result = cv2.matchTemplate(screen_img, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            # 计算按钮中心位置
            button_x = max_loc[0] + template.shape[1] // 2
            button_y = max_loc[1] + template.shape[0] // 2
            return (button_x, button_y)
        return None

    def save_template(self):
        """
        保存登录按钮的模板图片
        注意：运行这个函数时，请确保微信登录按钮可见
        """
        try:
            screen = self.capture_screen()
            # 假设登录按钮在屏幕中间，截取中间区域
            height, width = screen.shape[:2]
            center_x, center_y = width // 2, height // 2
            
            # 截取按钮区域（根据实际按钮大小调整）
            button_width, button_height = 100, 40  # 根据实际按钮大小调整
            button_region = screen[
                center_y - button_height:center_y + button_height,
                center_x - button_width:center_x + button_width
            ]
            
            cv2.imwrite(self.login_button_template, button_region)
            print(f"模板已保存到: {self.login_button_template}")
            return True
        except Exception as e:
            print(f"保存模板失败: {str(e)}")
            return False

    def click_wechat_login(self):
        """模拟点击微信登录按钮"""
        try:
            # 查找微信窗口
            hwnd = self.find_wechat_window()
            if not hwnd:
                return False, "未找到微信窗口"

            # 将窗口置于前台
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)

            # 等待窗口激活
            pyautogui.sleep(0.5)

            # 捕获屏幕并查找按钮
            screen = self.capture_screen()
            button_pos = self.find_button_position(screen, self.login_button_template)

            if button_pos:
                # 点击按钮
                pyautogui.click(button_pos[0], button_pos[1])
                return True, "登录按钮点击成功"
            else:
                return False, "未找到登录按钮"

        except Exception as e:
            return False, f"点击失败: {str(e)}"

helper = WeChatLoginHelper()

@app.route('/trigger-login', methods=['POST'])
def trigger_login():
    """处理登录请求的API端点"""
    success, message = helper.click_wechat_login()
    return jsonify({
        'success': success,
        'message': message
    })

@app.route('/save-template', methods=['POST'])
def save_template():
    """保存按钮模板的API端点"""
    success = helper.save_template()
    return jsonify({
        'success': success,
        'message': "模板保存成功" if success else "模板保存失败"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5001)