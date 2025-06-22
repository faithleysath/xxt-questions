import tkinter as tk
from tkinter import messagebox, ttk
import json
import random

class QuizApp:
    """一个从JSON文件加载题目的Tkinter测验应用"""

    def __init__(self, root):
        """初始化应用"""
        self.root = root
        self.root.title("测验程序")
        self.root.geometry("800x600")

        # 设置样式
        self.style = ttk.Style()
        self.style.configure("TLabel", font=("Helvetica", 12))
        self.style.configure("TButton", font=("Helvetica", 11))
        self.style.configure("Header.TLabel", font=("Helvetica", 16, "bold"))
        self.style.configure("Stem.TLabel", font=("Helvetica", 14))
        self.style.configure("TCheckbutton", font=("Helvetica", 12))
        
        # 初始化变量
        self.all_questions = []
        self.quiz_questions = []
        self.user_answers = {}
        self.current_question_index = 0
        
        # 加载题目
        self.load_questions()
        
        # 创建初始设置界面
        self.create_setup_frame()

    def clear_frame(self):
        """清空主窗口的所有组件"""
        for widget in self.root.winfo_children():
            widget.destroy()

    def load_questions(self):
        """从题库.json文件加载题目"""
        try:
            with open("题库.json", "r", encoding="utf-8") as f:
                self.all_questions = json.load(f)
        except FileNotFoundError:
            messagebox.showerror("错误", "未找到 '题库.json' 文件！\n请确保该文件与程序在同一目录下。")
            self.root.quit()
        except json.JSONDecodeError:
            messagebox.showerror("错误", "'题库.json' 文件格式不正确！")
            self.root.quit()

    def create_setup_frame(self):
        """创建用于设置题目数量的初始界面"""
        self.clear_frame()
        setup_frame = ttk.Frame(self.root, padding="20")
        setup_frame.pack(expand=True)

        ttk.Label(setup_frame, text="欢迎来到测验程序", style="Header.TLabel").pack(pady=20)
        
        info_text = f"题库中共有 {len(self.all_questions)} 道题。\n请输入要抽取的题目数量："
        ttk.Label(setup_frame, text=info_text, justify=tk.CENTER).pack(pady=10)

        self.num_questions_entry = ttk.Entry(setup_frame, width=10, font=("Helvetica", 12))
        self.num_questions_entry.pack(pady=5)

        start_button = ttk.Button(setup_frame, text="开始测验", command=self.start_quiz)
        start_button.pack(pady=20)

    def start_quiz(self):
        """根据用户输入开始测验"""
        try:
            num_to_draw = int(self.num_questions_entry.get())
            if not (0 < num_to_draw <= len(self.all_questions)):
                raise ValueError
        except ValueError:
            messagebox.showwarning("输入无效", f"请输入一个介于1和{len(self.all_questions)}之间的数字。")
            return
        
        # 随机抽取题目
        self.quiz_questions = random.sample(self.all_questions, num_to_draw)
        self.user_answers = {} # 重置答案记录
        self.current_question_index = 0
        
        self.display_question()

    def display_question(self):
        """显示当前题目和选项"""
        self.clear_frame()
        
        # 获取当前题目数据
        question_data = self.quiz_questions[self.current_question_index]
        stem = question_data["stem"]
        options = question_data["options"]
        
        # 顶部进度条
        progress_text = f"题目 {self.current_question_index + 1} / {len(self.quiz_questions)}"
        ttk.Label(self.root, text=progress_text, style="Header.TLabel").pack(pady=(10, 20))

        # 题干区域
        stem_frame = ttk.Frame(self.root, padding=(20, 10))
        stem_frame.pack(fill="x")
        stem_label = ttk.Label(stem_frame, text=stem, wraplength=750, justify=tk.LEFT, style="Stem.TLabel")
        stem_label.pack(anchor="w")

        # 选项区域
        self.option_vars = []
        options_frame = ttk.Frame(self.root, padding=(40, 10))
        options_frame.pack(fill="x")
        
        for i, option_data in enumerate(options):
            option_text = option_data[0]
            var = tk.BooleanVar()
            
            # 检查之前是否已保存答案
            if self.user_answers.get(self.current_question_index, {}).get(i, False):
                var.set(True)
            
            self.option_vars.append(var)
            
            cb = ttk.Checkbutton(options_frame, text=option_text, variable=var, style="TCheckbutton")
            cb.pack(anchor="w", pady=5)

        # 导航按钮区域
        self.create_navigation_buttons()
    
    def create_navigation_buttons(self):
        """创建上一题、下一题、提交按钮"""
        nav_frame = ttk.Frame(self.root, padding="20")
        nav_frame.pack(side="bottom", fill="x")

        # 上一题按钮
        prev_button = ttk.Button(nav_frame, text="上一题", command=self.prev_question)
        if self.current_question_index == 0:
            prev_button.state(['disabled'])
        prev_button.pack(side="left")

        # 提交按钮（仅在最后一题显示）
        if self.current_question_index == len(self.quiz_questions) - 1:
            submit_button = ttk.Button(nav_frame, text="提交问卷", command=self.submit_quiz)
            submit_button.pack(side="right")
        else:
            # 下一题按钮
            next_button = ttk.Button(nav_frame, text="下一题", command=self.next_question)
            next_button.pack(side="right")

    def save_current_answer(self):
        """保存当前题目的作答情况"""
        answers = {}
        for i, var in enumerate(self.option_vars):
            if var.get():
                answers[i] = True
        self.user_answers[self.current_question_index] = answers

    def next_question(self):
        """切换到下一题"""
        self.save_current_answer()
        self.current_question_index += 1
        self.display_question()

    def prev_question(self):
        """切换到上一题"""
        self.save_current_answer()
        self.current_question_index -= 1
        self.display_question()
    
    def submit_quiz(self):
        """提交问卷并计算分数"""
        self.save_current_answer()
        
        score = 0
        for i, question_data in enumerate(self.quiz_questions):
            correct_options = {idx for idx, opt in enumerate(question_data["options"]) if opt[1]}
            user_selected_options = set(self.user_answers.get(i, {}).keys())
            
            if correct_options == user_selected_options:
                score += 1
        
        total_questions = len(self.quiz_questions)
        result_title = "测验完成！"
        result_message = f"你的得分: {score} / {total_questions}"
        messagebox.showinfo(result_title, result_message)
        
        self.show_results()

    def show_results(self):
        """在主窗口展示详细作答结果"""
        self.clear_frame()

        # 创建一个带滚动条的Canvas
        canvas = tk.Canvas(self.root)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        ttk.Label(scrollable_frame, text="答题详情回顾", style="Header.TLabel").pack(pady=10)

        for i, q_data in enumerate(self.quiz_questions):
            result_frame = ttk.Frame(scrollable_frame, padding=10, relief="groove", borderwidth=2)
            result_frame.pack(padx=10, pady=5, fill="x")
            
            # 判断对错
            correct_opts_set = {idx for idx, opt in enumerate(q_data["options"]) if opt[1]}
            user_opts_set = set(self.user_answers.get(i, {}).keys())
            is_correct = (correct_opts_set == user_opts_set)
            
            result_text = "正确" if is_correct else "错误"
            result_color = "green" if is_correct else "red"
            
            # 题干
            header = f"题目 {i+1}: ({result_text})"
            ttk.Label(result_frame, text=header, foreground=result_color, font=("Helvetica", 13, "bold")).pack(anchor="w")
            ttk.Label(result_frame, text=q_data['stem'], wraplength=700, justify=tk.LEFT).pack(anchor="w", pady=(5,10))

            # 你的答案
            user_ans_texts = [q_data['options'][idx][0] for idx in user_opts_set]
            if not user_ans_texts: user_ans_texts.append("未作答")
            ttk.Label(result_frame, text=f"你的答案: {', '.join(user_ans_texts)}", foreground="blue").pack(anchor="w")
            
            # 正确答案
            correct_ans_texts = [q_data['options'][idx][0] for idx in correct_opts_set]
            ttk.Label(result_frame, text=f"正确答案: {', '.join(correct_ans_texts)}", foreground="green").pack(anchor="w")


if __name__ == "__main__":
    root = tk.Tk()
    app = QuizApp(root)
    root.mainloop()