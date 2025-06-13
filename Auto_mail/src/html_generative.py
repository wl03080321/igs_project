from typing import List, Tuple
def generate_combined_html(tableau_links: List[Tuple[str, str]], grouped_result: dict, class_map: dict = None) -> str:
    tableau_section = generate_tableau_html_body(tableau_links)
    report_section = generate_html_report(grouped_result, class_map=class_map)

    full_html = f"""
    <html>
      <head><meta charset="utf-8"></head>
      <body>
        {tableau_section}
        <hr>
        {report_section}
      </body>
    </html>
    """
    return full_html

def generate_tableau_html_body(dashboard_links: List[Tuple[str, str]], title: str = "📊 Tableau Dashboard 報表清單") -> str:
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
    </style>
    """

    for company, records in grouped_result.items():
        html += f"<h2>📊 公司：{company}</h2>\n"

        if records:
            keys = list(records[0].keys())
            html += "<table>\n<thead><tr>"
            for key in keys:
                html += f"<th>{key.capitalize()}</th>"
            html += "</tr></thead>\n<tbody>\n"

            for record in records:
                html += "<tr>"
                for key in keys:
                    value = str(record.get(key, "")).replace("\n", "<br>")
                    css_class = class_map.get(key, "") if class_map else ""

                    if css_class:
                        html += f"<td><div class='{css_class}'>{value}</div></td>"
                    else:
                        html += f"<td>{value}</td>"
                html += "</tr>\n"

            html += "</tbody></table>\n"

    return html
