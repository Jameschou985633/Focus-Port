import sqlite3, json, time
from pathlib import Path
from openai import OpenAI

DEEPSEEK_API_KEY = "sk-181b1df1d8b74a20bb261783511d317a"
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")


BASE_DIR = Path(__file__).resolve().parent
PRIMARY_DB_PATH = BASE_DIR / "focusport.db"
LEGACY_DB_PATH = BASE_DIR / "focuscrossing.db"


def resolve_db_path():
    if PRIMARY_DB_PATH.exists() or not LEGACY_DB_PATH.exists():
        return PRIMARY_DB_PATH
    return LEGACY_DB_PATH


def ai_grade_paper(ai_prompt, answers_dict):
    prompt = f"""
    【题目阅卷标准及满分】：
    {ai_prompt}

    【该学生的实际作答内容】（JSON格式）：
    {json.dumps(answers_dict, ensure_ascii=False)}

    【批改任务与绝对要求】：
    1. 指出学生作答中的语法错误、拼写错误及中式英语。
    2. 根据我提供的满分标准，给出一个合理的总分（数字类型，可带一位小数）。
    3. 写一段详细的中文评语。
    4. 🌟【极其重要】：你必须在评语的最后，附上一篇针对该题目要求的高质量【范文】（如果是翻译题，则附上【标准参考译文】），供学生学习对照！

    必须严格返回如下 JSON 格式：
    {{ "score": 12.5, "feedback": "【总体评价】...\\n【纠错】...\\n\\n【参考范文/译文】：\\n..." }}
    """
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": "你是一位大学英语阅卷教授，必须输出 JSON。"},
                      {"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        res = json.loads(response.choices[0].message.content)
        return res.get("score", 0), res.get("feedback", "评语生成失败")
    except Exception as e:
        print(f"❌ 出错: {e}")
        return 0, "AI 老师开小差了..."


def run_ai_teacher():
    conn = sqlite3.connect(resolve_db_path())
    cursor = conn.cursor()
    cursor.execute(
        '''SELECT s.id, s.username, s.exam_code, s.subjective_answers, e.ai_prompt FROM Exam_Submissions s JOIN Exams e ON s.exam_code = e.exam_code WHERE s.subjective_score = 0''')
    papers = cursor.fetchall()

    for paper in papers:
        exam_id, student_name, exam_code, answers_raw, ai_prompt = paper
        print(f"⏳ 正在批改 【{student_name}】 的试卷...")
        try:
            answers = json.loads(answers_raw)
        except:
            answers = answers_raw

        if not answers or (isinstance(answers, dict) and len(answers) == 0) or all(
                not v.strip() for v in answers.values()):
            score, feedback = 0, "交了白卷。下次勇敢动笔哦！"
        else:
            score, feedback = ai_grade_paper(ai_prompt, answers)
            print(f"✅ 批改完成！得分: {score}")

        cursor.execute('UPDATE Exam_Submissions SET subjective_score = ?, teacher_feedback = ? WHERE id = ?',
                       (score, "【🐳 DeepSeek 批阅与范文】\n\n" + feedback, exam_id))
        conn.commit()
        time.sleep(1)

    print("🎊 批改完毕！")
    conn.close()


if __name__ == "__main__":
    run_ai_teacher()
