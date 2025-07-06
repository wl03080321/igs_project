from typing import List, Tuple
import re

def highlight_page_references(text):
    """檢測並高亮頁碼引用"""
    # 正規表達式匹配 (p.數字) 或 (p.數字-數字) 或包含多個頁碼的格式
    pattern = r'[(\（]p\.\s*\d+(?:-\d+)?(?:\s*,\s*p\.\s*\d+(?:-\d+)?)*[)\）]'
    
    def replace_match(match):
        page_ref = match.group(0)
        return f"<span class='page-reference'>{page_ref}</span>"
    
    return re.sub(pattern, replace_match, text, flags=re.IGNORECASE)

def generate_combined_html(tableau_data: dict[Tuple[str, str]] = None, grouped_result: dict = None, class_map: dict = None, quarter: str = "") -> str:
    print(tableau_data)
    report_section = generate_html_report(grouped_result, class_map=class_map)
    tableau_link = ""
    if tableau_data is not None and "url" in tableau_data:
        tableau_link = tableau_data["url"]
    print("Tableau link:", tableau_link)
    quarter = quarter.replace("_", "年")
    full_html = f"""
    <html>
      <head><meta charset="utf-8"></head>
      <body>
        <p>各位主管同仁好：</p>
        <p>以下為美國競業廠商{quarter}報告重點摘要</p>
        <a href="{tableau_link}" target="_blank", style="font-size: 20px; font-weight: bold; color: #216ebb;">
            營收趨勢
        </a>
        <hr>
        {report_section}
      </body>
    </html>
    """
    return full_html

def generate_tableau_html_body(dashboard_links: List[Tuple[str, str]], title: str = "📊 Tableau Dashboard 報表清單") -> str:
    if dashboard_links == []:
        return "<p>沒有可用的 Tableau Dashboard 連結。</p>"
    
    html_body = f"""
    <h2>{title}</h2>
    <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse;">
      <tr style="background-color: #f2f2f2;">
        <th align="left">報表名稱</th>
        <th align="left">Dashboard 連結</th>
      </tr>
    """
    for name, url in dashboard_links:
        html_body += f"""
          <tr>
            <td>{name}</td>
            <td><a href="{url}" target="_blank">{url}</a></td>
          </tr>
        """
    html_body += "</table>\n"
    return html_body
    
def generate_html_report(grouped_result: dict, class_map: dict = None):
    if not grouped_result:
        return "<p>沒有可用的公司資料。</p>"
    
    html = """
    <style>
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 40px;
        }
        th, td {
            border: 1px solid #ccc;
            padding: 10px;
            vertical-align: top;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
        }
        .analysis {
            white-space: pre-wrap;
            font-family: Arial, sans-serif;
            max-height: 50px;
            overflow-y: auto;
            padding: 5px;
            background-color: #f9f9f9;
            border: 1px solid #ddd;
        }
        .bold-column {
            font-weight: bold;
            color: #2c3e50;
        }
        
        .page-reference {
            background-color: #e3f2fd;
            color: #1976d2;
            padding: 2px 4px;
            border-radius: 3px;
            font-weight: bold;
            border: 1px solid #1976d2;
        }
        
    </style>
    """
    
    for company, records in grouped_result.items():
        html += f"<a style=\"font-size: 20px;\">{company}</a>"
        if records and "link" in records[0]:
            html += f"<span style=\"font-size: 20px;\">(<a href=\"{records[0]['link']}\" target=\"_blank\" style=\"background-color: #ced12e\">財報連結</a>)</span>"
        if records:
            keys = list(records[0].keys())
            html += "<table>\n<tbody>\n"
            #html += "<thead><tr>"
            
            # for key in keys:
            #     html += f"<th>{key.capitalize()}</th>"
            #html += "</tr></thead>\n<tbody>\n"

            for record in records:
                html += "<tr>"
                for key in keys:
                    if key != "title" and key != "analysis":
                        continue
                    value = str(record.get(key, "")).replace("\n", "<br>")
                    css_class = class_map.get(key, "") if class_map else ""
                    if key == "analysis":
                        value = highlight_page_references(value)
                    if css_class:
                        html += f"<td><div class='{css_class}'>{value}</div></td>"
                    else:
                        html += f"<td>{value}</td>"
                html += "</tr>\n"

            html += "</tbody></table>\n"
    return html
