"""
对部分字段进行格式处理
"""
from pathlib import Path
import pandas as pd
import urllib
import re
import logging


def add_bracket(name):
    # 添加书名号
    if "http" in name:
        name = name.split("http")[0]
    name = name.strip()
    return name if "《" in name else (f"《{name}》" if name != "" else None)


def strip_words(s):
    s = re.sub(r"\s*\n+\s*", "||", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def format_links(link_text):
    links = link_text.split("\n")
    out = []
    for s in links:
        if s.lower().startswith("bv") or s.lower().startswith("av"):
            s = f"https://www.bilibili.com/video/{s}"  # b站视频转换完整网址
        elif s.startswith("http") and "bilibili" in s:
            s = s.split("?")[0].strip("/")  # 去除参数
            if s.endswith("/dynamic"):
                s = s.split("/dynamic")[0]
        elif "b23.tv" in s:  # 基本失效
            s = ""
        elif not s.startswith("http"):  # 错误格式
            # if s!='':
            #     print(s)
            if "http" in s:
                s = "http" + s.split("http")[1].split("；")[0]
            if "BV" in s:
                s = "https://www.bilibili.com/video/BV" + s.split("BV")[-1].split("BV")[
                    0
                ].strip("，、。")
            elif s.startswith("coursera.org"):
                s = "https://" + s
            if "bilibili" in s:
                s = s.split("?")[0]

            if not s.startswith("http"):
                s = ""
        out.append(urllib.parse.unquote(s))
    return out[0]


def update_platform(x):
    renamed = {
        "B站": [
            "BILIBILI",
            "BILBILI",
            "哔哩哔哩",
            "官方B站号",
            "B站授权发布",
            "B",
            "B站蠢杠杠",
            "B站自制",
            " B站官号",
            "B站官方",
        ],
        "YOUTUBE": ["YOUTUBE公开课", "油管"],
        "中国大学MOOC": [
            "中国大学慕课",
            "中国大学MOCC",
            "中国MOOC课",
            "MOOC网",
            "MOOC慕课",
            "慕课",
        ],
        "网易公开课": ["网易云课堂"],
        "臺大開放式課程": ["台湾大学公开课"],
        "无": [
            "无？",
            "",
            "1",
            "1231",
            "他",
            "几天",
            "活动结束",
            "暂时没找到",
            "网站",
            "看看",
            "C占",
        ],
        "超星": ["超星学术视频", "超星慕课", "超星学习通", "学习通", "超星名师"],
        "爱课程": ["爱课程APP", "ICOURSE爱课程"],
        "COURSERA": ["COURSERA免费课程"],
        "北京师范大学": ["北师大官网", "北京师范大学官网"],
        "EDX": ["COURSES.EDX"],
    }

    name2 = [
        "B站",
        "中国大学MOOC",
        "无",
        "爱课程",
        "网易公开课",
        "学堂在线",
        "COURSERA",
        "MOOC",
        "超星",
        "YOUTUBE",
        "臺大開放式課程",
        "辽宁资源共享",
        "学习强国",
    ]

    x = x.split(" ")[0]
    if "bilibili" in x:
        x = "B站"

    out = re.split("([（(]|官方账号|UP|@|哔站)", x.upper())[0]
    out = re.sub(r"B\s+站", "B站", out)
    out = re.sub(r"[及、，；]", "/", out)
    for k, v in renamed.items():
        if out in v:
            out = k
            break
    if "B站" in out or "哔哩哔哩" in out:
        out = "B站"
    elif "中国大学MOOC" in out:
        out = "中国大学MOOC"
    elif "网易公开课" in out:
        out = "网易公开课"
    elif "腾讯" in out:
        out = "腾讯课堂"
    elif "爱奇艺" in out:
        out = "爱奇艺"
    if not (out in renamed or out in name2):
        out = "其他"
    return out


def update_platform2(s):
    s = s.upper()
    if "B" in s or "小破站" in s or "哔" in s:
        return "B站"
    return "其他"



def set_link(platform, link):
    if link.startswith("http"):
        return f"[{platform}]({link})"
    return platform


def format_csv1(file, savefile):
    df = pd.read_csv(file)
    df2 = df.drop(columns=["index"]).copy()
    logging.info(f"df = {df2.shape}, columns = {df2.columns}")

    out_cols = [
        "推荐课程名称",
        "授课老师",
        "课程对应专业",
        "平台及链接",
        "推荐人ID",
        "推荐人专业",
        "推荐语",
        "推荐日期",
    ]
    sort_cols = ["课程对应专业", "推荐课程名称", "推荐人ID"]
    

    col1, col2 = "授课老师", "推荐课程名称"
    start_idx = 809
    t1 = df2.loc[start_idx:][col1].copy()
    t2 = df2.loc[start_idx:][col2].copy()
    df2.loc[start_idx:, col1] = t2
    df2.loc[start_idx:, col2] = t1

    col = "推荐课程名称"
    df2.loc[df2[col].replace("", None).isnull(), col] = df2["课程对应专业"]
    df2[col] = df2[col].fillna("").apply(add_bracket)
    df2 = df2[df2[out_cols[0]].notnull()].copy()
    
    for col in ["推荐语", "授课老师"]:
        df2[col] = df2[col].fillna("").apply(strip_words)

    logging.info(f"{df2.columns}")
    df2["links"] = df2["跳转链接"].fillna("").apply(format_links)
    df2["platform"] = df2["课程所在平台"].fillna("").apply(update_platform)
    df2["平台及链接"] = df2.apply(lambda x: set_link(x["platform"], x["links"]), axis=1)

    df3 = df2[out_cols].fillna(" ")
    df3 = df3.sort_values(sort_cols)
    df3.reset_index(drop=True).reset_index().to_csv(savefile, index=False)

def format_csv2(file, savefile):
    df = pd.read_csv(file)
    df2 = df.drop(columns=["index"]).copy()
    if file.stem == "其他课程区":
        df2 = df2.rename(columns={"4.推荐课程对应领域": "推荐课程对应领域"})
        col = "推荐课程名称"
        df2[col] = df2[col].fillna("").apply(add_bracket)

        col_platform = "课程所在平台"
        out_cols = [
            "推荐课程名称",
            "老师（博主）名称",
            "推荐课程对应领域",
            "平台及链接",
            "推荐人ID",
            "推荐理由",
            "推荐日期",
        ]
        sort_cols = ["推荐课程对应领域", "推荐课程名称", "推荐人ID"]
    else:
        col_platform = "博主所在平台"
        out_cols = [
            "推荐博主名称",
            "博主涉及领域",
            "平台及链接",
            "推荐人ID",
            "推荐理由",
            "推荐时间",
        ]
        sort_cols = ["博主涉及领域", "推荐博主名称", "推荐人ID"]

    df2 = df2[df2[out_cols[0]].notnull()].copy()
    for col in ["推荐理由", "老师（博主）名称", "推荐课程对应领域"]:
        if col in df2.columns:
            df2[col] = df2[col].fillna("").apply(strip_words)
    df2["links"] = df2["跳转链接"].fillna("").apply(format_links)
    df2["platform"] = df2[col_platform].fillna("").apply(update_platform2)
    df2["平台及链接"] = df2.apply(lambda x: set_link(x["platform"], x["links"]), axis=1)

    df3 = df2[out_cols].fillna(" ")
    df3 = df3.sort_values(sort_cols)
    df3.reset_index(drop=True).reset_index().to_csv(savefile, index=False)


def strip_book(name):
    name = re.sub(r"\s+", " ", name)
    name = re.split(r"[（(]", name)[0].strip()
    if '《' in name:
        name = name.split("《")[1].split("》")[0].strip()
    # 修正标点，去除中文中间空格
    for p1, p2 in [[":","："],["-","——"],[r"\s+", ""]]:
        name = re.sub(rf'([\u4e00-\u9fa5]){p1}([\u4e00-\u9fa5])', rf'\1{p2}\2', name)
    name = name.strip()
    
    if name in ['', 'a', '1', 'lool','，','我']:
        return None
    
    if name in ['一九八四 1984', '1984']:
        name = '一九八四'
    if name in ['三体全集']:
        name = '三体'
    if ' ' in name and '出版社' in name:
        name = name.split()[0]
    name = name.capitalize()
    return f"《{name}》"

def format_book(file, savefile):
    df = pd.read_csv(file)
    df2 = df.drop(columns=["index"]).copy()
    out_cols = ["推荐书籍名称", "书籍作者", "推荐人ID", "推荐语", "推荐日期"]
    sort_cols = out_cols[:3]
    
    col = out_cols[0]
    df2[col] = df2[col].fillna("").apply(strip_book)
    df2 = df2[df2[col].notnull()].copy()
    
    for col in ["书籍作者", "推荐语"]:
        df2[col] = df2[col].fillna("").apply(strip_words)
    df3 = df2[out_cols].fillna(" ")
    df3 = df3.sort_values(sort_cols)
    df3.reset_index(drop=True).reset_index().to_csv(savefile, index=False)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(filename)s [line:%(lineno)d] %(levelname)s %(message)s",
    )
    fn_names = [
        # [format_csv1, ["大学专业类课程区"]],
        # [format_csv2, ["其他课程区", "up主推荐区"]],
        [format_book, ["推荐书籍区"]],
    ]
    basedir = "data/raw"
    savedir = Path("data/csv")
    if not savedir.exists():
        savedir.mkdir(parents=True)
    for fn, names in fn_names:
        for name in names:
            file = Path(basedir, f"{name}.csv")
            savefile = Path(savedir, f"{name}.csv")
            logging.info(f"process {name} ...")
            if not file.exists():
                logging.error(f"{file} does not exist")
            fn(file, savefile)
