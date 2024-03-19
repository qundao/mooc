"""
下载腾讯文档并转成CSV。
"""
import logging
import re
import requests
import numpy as np

import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path


table_id = "DRU5MWHZCTHFGQnhM"
sheets = [
    # {'hidden': False, 'name': '首页导航', 'id': 'qb1sze', 'type': 'grid'},
    # {'hidden': False, 'name': '指南&必读', 'id': 'p29myi', 'type': 'grid'},
    # {'hidden': False, 'name': '专题活动', 'id': 'nvistz', 'type': 'grid'},
    {"hidden": False, "name": "大学专业类课程区", "id": "ykvdlu", "type": "grid"},
    {"hidden": False, "name": "其他课程区", "id": "ev0qh9", "type": "grid"},
    {"hidden": False, "name": "up主推荐区", "id": "m112fj", "type": "grid"},
    {"hidden": False, "name": "推荐书籍区", "id": "q4v4sc", "type": "grid"},
]


def get_excel_date(excel_date):
    # excel日期处理
    converted_date = None
    try:
        if excel_date.count('.') == 2:
            converted_date = datetime.strptime(excel_date, '%Y.%m.%d')
        elif excel_date.count('/') == 2:
            converted_date = datetime.strptime(excel_date, '%Y/%m/%d')
        else:
            excel_date = float(excel_date)
            if excel_date > 0:
                # Excel中的起始日期（1900年1月1日）
                start_date = datetime(1899, 12, 30)
                delta = timedelta(days=excel_date)
                converted_date = start_date + delta
        return converted_date.strftime('%Y-%m-%d %H:%M:%S') if converted_date else None
    except:
        return excel_date


def get_doc_data(table_id, sheet_id):
    # 获取腾讯文档数据
    referer = f"https://docs.qq.com/sheet/{table_id}?tab={sheet_id}"
    headers = {"referer": referer, "authority": "docs.qq.com", "accept": "*/*"}
    url = f"https://docs.qq.com/dop-api/opendoc?tab={sheet_id}&id={table_id}&outformat=1&normal=1"
    
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        logging.warning(f"Error status = {res.status_code}")
        return None
    return res.json()

def strip(s):
    # remove newlines and spaces
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s*\n+\s*", "\n", s) # 暂时保留换行
    return s.strip()

def parse_to_csv(name, sheet_id, savefile, startrow=4):
    logging.info(f"process {name} {sheet_id}")
    raw = get_doc_data(table_id, sheet_id)
    if not raw:
        return

    last_update = raw["bodyData"]["lastSaveTimestamp"]
    data = raw["clientVars"]["collab_client_vars"]
    last_update = raw['bodyData']['lastSaveTimestamp']
    maxcol, maxrow = data["maxCol"], data["maxRow"]
    table = data["initialAttributedText"]["text"][0][-1][0]["c"][1]
    logging.info(f"last_update = {last_update}, max col = {maxcol}, row = {maxrow}")
    logging.info(f"data table = {len(table)}")
    table2 = {i: table.get(str(i), {}).get("2") for i in range(maxcol * maxrow)}

    df = pd.DataFrame([table2]).T
    logging.info(f"df = {df.shape}")
    df[1] = df[0].apply(lambda x: strip(str(x[-1])) if isinstance(x, list) else None)
    df[1] = df[1].replace("", None)

    df2 = pd.DataFrame(np.reshape(df[1].values, (maxrow, maxcol)))
    logging.info(f"reshape, df = {df.shape}")

    dfi = df2.isnull().sum(axis=0)
    cols = dfi[dfi != maxrow].index.tolist()  # 去除全空的列

    # 表头和数据
    new_cols = df2[cols].iloc[startrow].tolist()
    df3 = df2[cols].iloc[startrow + 1 :].reset_index(drop=True)
    df3.columns = new_cols
    logging.info(f"Update df = {df3.shape}")

    # 更新日期
    logging.info("Update date column")
    date_col = "推荐日期" if "推荐日期" in new_cols else "推荐时间"
    df3[date_col] = df3[date_col].fillna("0").astype("str").apply(get_excel_date)
    
    # 删除全空的行
    df4 = df3[df3.notnull().sum(axis=1) > 0]
    df4 = df4.reset_index()
    logging.info(f"df = {df4.shape}, cols = {df4.columns.tolist()}")

    logging.info(f"save to {savefile}")
    df4.to_csv(savefile, index=False)


def run(savedir):
    for sheet in sheets:
        name, sheet_id = sheet["name"], sheet["id"]
        savefile = Path(savedir, f"{name}.csv")
        parse_to_csv(name, sheet_id, savefile)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(filename)s [line:%(lineno)d] %(levelname)s %(message)s",
    )
    savedir = Path("data/raw")
    if not savedir.exists():
        savedir.mkdir(parents=True)

    run(savedir)
