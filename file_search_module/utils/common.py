import datetime

def format_modified_date(timestamp):
    """
    若是當前年分，顯示 M月D日；否則顯示 YY/MM/DD。
    """
    dt = datetime.datetime.fromtimestamp(timestamp)
    current_year = datetime.datetime.now().year
    if dt.year == current_year:
        return f"{dt.month}月{dt.day}日"
    else:
        return dt.strftime("%y/%m/%d")
