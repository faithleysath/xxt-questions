import json
import argparse
import time
import pandas as pd
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, WebDriverException

# 定义一个全局的字母表，用于根据顺序确定选项
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def js_click(driver, element):
    """
    使用JavaScript执行点击，以绕过元素遮挡问题。
    """
    driver.execute_script("arguments[0].click();", element)

# --- 题目解析与提取模块 ---
def parse_questions(driver):
    """
    解析当前页面上的所有题目元素，并带有进度条。
    """
    all_questions_data = []
    question_elements = driver.find_elements(By.CLASS_NAME, 'questionLi')
    
    if not question_elements:
        print("未能找到类名为 'questionLi' 的题目。请检查页面内容或类名是否正确。")
        return all_questions_data

    print(f"找到了 {len(question_elements)} 道题目，正在开始解析...")

    for q_element in tqdm(question_elements, desc="正在解析题目"):
        try:
            q_type_text = q_element.find_element(By.CSS_SELECTOR, 'h3.mark_name > span.colorShallow').text
            q_type = q_type_text.strip('()')
            full_stem_text = q_element.find_element(By.CSS_SELECTOR, 'h3.mark_name').get_attribute('textContent').strip()
            q_stem = ')'.join(full_stem_text.split(')')[1:]).strip()

            correct_answer_letters = []
            try:
                mark_key_div = q_element.find_element(By.CSS_SELECTOR, 'div.mark_key')
                spans = mark_key_div.find_elements(By.TAG_NAME, 'span')
                for span in spans:
                    if "正确答案:" in span.get_attribute('textContent'):
                        answer_text = span.get_attribute('textContent').replace('正确答案:', '').strip()
                        if answer_text:
                            correct_answer_letters = list(answer_text)
                        break
            except NoSuchElementException:
                pass
            
            options_list = []
            option_elements = q_element.find_elements(By.CSS_SELECTOR, 'div.stem_answer > div.clearfix')
            for index, opt_element in enumerate(option_elements):
                option_letter = LETTERS[index]
                option_text = opt_element.find_element(By.CSS_SELECTOR, 'div.answer_p').text
                is_correct = option_letter in correct_answer_letters
                options_list.append((option_text, is_correct))

            question_data = {
                "type": q_type,
                "stem": q_stem,
                "options": options_list
            }
            all_questions_data.append(question_data)

        except Exception as e:
            tqdm.write(f"解析某道题目时出错: {e}")
            continue

    return all_questions_data

# --- 自动选择答案模块 ---
def auto_select_answers(driver, question_bank, delay):
    """
    自动在页面上选择题目的正确答案。
    """
    print(f"开始自动选择答案 (操作延迟: {delay}秒)...")
    question_elements = driver.find_elements(By.CLASS_NAME, 'questionLi')
    if not question_elements:
        print("未找到题目，无法执行自动选择。")
        return

    unmatched_count = 0
    for q_element in tqdm(question_elements, desc="正在自动答题"):
        correct_answer_letters = []
        try:
            answer_text_raw = q_element.find_element(By.XPATH, ".//span[contains(., '正确答案:')]").text
            correct_answer_letters = list(answer_text_raw.replace('正确答案:', '').strip())
        except NoSuchElementException:
            try:
                full_stem_text = q_element.find_element(By.CSS_SELECTOR, 'h3.mark_name').get_attribute('textContent').strip()
                q_stem = ')'.join(full_stem_text.split(')')[1:]).strip()
                found_in_bank = False
                for item in question_bank:
                    if item['stem'] == q_stem:
                        for i, (opt_text, is_correct) in enumerate(item['options']):
                            if is_correct:
                                correct_answer_letters.append(LETTERS[i])
                        found_in_bank = True
                        break
                if not found_in_bank:
                    unmatched_count += 1
                    tqdm.write(f"警告: 题库中未找到题目 '{q_stem[:30]}...' 的答案。")
                    continue
            except Exception as e:
                tqdm.write(f"从题库匹配时发生错误: {e}")
                continue

        if not correct_answer_letters:
            tqdm.write("警告: 未能找到当前题目的任何答案来源。")
            continue

        try:
            # 取消所有已选中的选项
            selected_options = q_element.find_elements(By.CSS_SELECTOR, ".check_answer, .check_answer_dx")
            for selected_opt_span in selected_options:
                option_div_to_uncheck = selected_opt_span.find_element(By.XPATH, "..")
                js_click(driver, option_div_to_uncheck)
                time.sleep(delay)

            # 点击正确答案
            all_option_divs = q_element.find_elements(By.CSS_SELECTOR, "div.stem_answer > div.clearfix")
            for index, option_div in enumerate(all_option_divs):
                current_option_letter = LETTERS[index]
                if current_option_letter in correct_answer_letters:
                    js_click(driver, option_div)
                    time.sleep(delay)
        except Exception as e:
            tqdm.write(f"点击选项时出错: {e}")

    print(f"\n自动选择完成！")
    if unmatched_count > 0:
        print(f"提示: 有 {unmatched_count} 道题目因无法在页面或题库中找到答案而未作答。")


# --- 修改：将题库JSON转换为Excel (xlsx) ---
def export_to_excel(question_bank, output_filename):
    """
    将题库数据（字典列表）转换为Excel文件。
    """
    if not question_bank:
        print("错误: 题库为空，无法导出。")
        return

    print(f"正在将 {len(question_bank)} 道题目转换为Excel格式...")
    processed_questions = []
    for q in tqdm(question_bank, desc="转换进度"):
        question_data = {
            '题型': q['type'],
            '题干': q['stem']
        }
        correct_answers = []
        for i, (option_text, is_correct) in enumerate(q['options']):
            option_letter = LETTERS[i]
            question_data[f'选项{option_letter}'] = option_text
            if is_correct:
                correct_answers.append(option_letter)
        
        question_data['答案'] = ''.join(correct_answers)
        processed_questions.append(question_data)

    df = pd.DataFrame(processed_questions)
    
    max_options = 0
    if question_bank:
      max_options = max(len(q['options']) for q in question_bank) if any(q['options'] for q in question_bank) else 0

    column_order = ['题型', '题干'] + [f'选项{LETTERS[i]}' for i in range(max_options)] + ['答案']
    df = df.reindex(columns=column_order)

    try:
        # 使用 to_excel 保存，需要 openpyxl 引擎
        df.to_excel(output_filename, index=False, engine='openpyxl')
        print(f"\n成功！题库已导出到 '{output_filename}'。")
    except Exception as e:
        print(f"\n导出Excel时发生错误: {e}")


# --- 主程序与菜单 ---
def main():
    """
    主函数，提供一个菜单来协调所有功能。
    """
    parser = argparse.ArgumentParser(
        description="一个交互式的超星学习通自动化工具。",
        formatter_class=argparse.RawTextHelpFormatter 
    )
    # 修改：参数名从 --output 改为 --db
    parser.add_argument("--db", type=str, default="题库.json", help="指定题库JSON数据库的文件名。\n(默认: 题库.json)")
    parser.add_argument("--url", type=str, help="预设要操作的URL。")
    parser.add_argument("--cookies", type=str, default="cookies.json", help="指定Cookies文件名。(默认: cookies.json)")
    parser.add_argument("--delay", type=float, default=0, help="每次点击操作之间的延迟(秒)。(默认: 0)")
    # 修改：参数从 --export-csv 改为 --export-excel
    parser.add_argument("--export-excel", type=str, metavar="FILENAME.xlsx", nargs='?', const="题库.xlsx",
                        help="将题库直接导出为Excel文件并退出。\n可以指定文件名，若不指定则默认为 '题库.xlsx'。")
    
    args = parser.parse_args()

    driver = None
    question_bank = []
    
    # 修改：使用 args.db 加载题库
    try:
        with open(args.db, 'r', encoding='utf-8') as f:
            question_bank = json.load(f)
        print(f"已成功加载本地题库 '{args.db}'，共 {len(question_bank)} 道题目。")
    except FileNotFoundError:
        print(f"本地题库 '{args.db}' 不存在，将在提取后创建。")
    except json.JSONDecodeError:
        print(f"警告: 题库文件 '{args.db}' 格式错误，无法解析。")

    # 修改：处理 --export-excel 参数
    if args.export_excel:
        if not question_bank:
            print(f"错误: 题库 '{args.db}' 为空或加载失败，无法执行导出。")
            return
        export_to_excel(question_bank, args.export_excel)
        return

    while True:
        print("\n" + "="*20 + " 主菜单 " + "="*20)
        print("1. 打开浏览器并导航到指定URL")
        print("2. 从当前页面提取题目到本地题库")
        print("3. 自动选择答案")
        # 修改：菜单文本更新
        print("4. 导出题库为Excel (xlsx)格式")
        print("0. 退出程序")
        print("="*52)
        
        choice = input("请输入您的选择: ").strip()

        if choice == '1':
            url = args.url
            if not url:
                url = input("请输入要打开的URL: ").strip()
            if not url:
                print("URL为空，操作取消。")
                continue
            
            try:
                print("正在启动浏览器...")
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service)
                
                if args.cookies:
                    try:
                        driver.get("https://mooc1.chaoxing.com/") 
                        with open(args.cookies, 'r') as f: cookies = json.load(f)
                        for cookie in cookies: driver.add_cookie(cookie)
                        print(f"成功从 '{args.cookies}' 加载Cookies。")
                    except FileNotFoundError:
                        print(f"Cookies文件 '{args.cookies}' 不存在，将在登录后创建。")
                    except Exception as e:
                        print(f"加载Cookies时出错: {e}")

                print(f"正在导航至目标URL: {url}")
                driver.get(url)
                args.url = url
                
                print("-" * 50)
                print("浏览器已打开。如果未能自动登录，请手动完成登录等操作。")
                input("当页面加载完毕后，请回到此窗口按 Enter 键确认...")
                
                if args.cookies:
                    with open(args.cookies, 'w') as f: json.dump(driver.get_cookies(), f)
                    print(f"登录状态已保存到 '{args.cookies}'。")
                print("-" * 50)

            except WebDriverException as e: print(f"打开浏览器或导航时出错: {e}")
            except Exception as e: print(f"发生未知错误: {e}")

        elif choice == '2':
            if not driver:
                print("错误: 请先选择 '1' 打开浏览器。")
                continue
            scraped_data = parse_questions(driver)
            if scraped_data:
                existing_stems = {item['stem'] for item in question_bank}
                new_items_count = 0
                for item in scraped_data:
                    if item['stem'] not in existing_stems:
                        question_bank.append(item)
                        existing_stems.add(item['stem'])
                        new_items_count += 1
                # 修改：使用 args.db 保存题库
                with open(args.db, 'w', encoding='utf-8') as f:
                    json.dump(question_bank, f, ensure_ascii=False, indent=4)
                print(f"\n成功提取 {len(scraped_data)} 道题目。其中 {new_items_count} 道新题已添加至 '{args.db}'。")
                print(f"题库现在总共有 {len(question_bank)} 道题目。")
            else:
                print("未能提取到任何题目。")

        elif choice == '3':
            if not driver:
                print("错误: 请先选择 '1' 打开浏览器。")
                continue
            if not question_bank:
                 print("警告: 本地题库为空，将仅依赖页面上可能存在的'正确答案'进行选择。")
            auto_select_answers(driver, question_bank, args.delay)
        
        # 修改：处理菜单 '4'
        elif choice == '4':
            if not question_bank:
                print("错误: 题库为空，请先使用选项 '2' 提取题目。")
                continue
            xlsx_filename = input("请输入要保存的Excel文件名 (按Enter默认为 '题库.xlsx'): ").strip()
            if not xlsx_filename:
                xlsx_filename = '题库.xlsx'
            # 确保文件名以 .xlsx 结尾
            if not xlsx_filename.lower().endswith('.xlsx'):
                xlsx_filename += '.xlsx'
            export_to_excel(question_bank, xlsx_filename)

        elif choice == '0':
            if driver:
                driver.quit()
            print("程序已退出。")
            break
            
        else:
            print("无效输入，请输入菜单中的数字。")

if __name__ == '__main__':
    # 运行前，请确保已安装必要的库：
    # pip install selenium webdriver-manager tqdm pandas openpyxl
    main()