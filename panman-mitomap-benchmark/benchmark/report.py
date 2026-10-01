#!/usr/bin/env python3
"""Generate TSV, HTML, Markdown and a Word document using the standard library."""
import csv
import html
import io
import json
import os
from pathlib import Path
import statistics
import zipfile
from xml.sax.saxutils import escape


STYLE = """body{font-family:'Microsoft YaHei','Noto Sans CJK SC',sans-serif;max-width:1080px;margin:40px auto;padding:0 28px;color:#18202a;line-height:1.7}h1,h2,h3{color:#000}h1{font-size:28px}h2{font-size:20px;margin-top:32px}table{border-collapse:collapse;width:100%;margin:14px 0 22px;font-size:14px}th,td{border:1px solid #d9d9d9;padding:9px 12px;text-align:left;overflow-wrap:anywhere}th{background:#dfebf5;color:#000}tr:nth-child(even){background:#f7f9fb}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.55 Consolas,monospace}code{font-family:Consolas,monospace}a{color:#125fa0}@media print{body{max-width:none;margin:0;padding:0;font-size:10.5pt}thead{display:table-header-group}tr{break-inside:avoid}h2,h3{break-after:avoid}table{font-size:9pt}}"""


def atomic_text(path, text):
    path = Path(path)
    tmp = path.with_name(path.name + ".partial")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def tsv(path, rows, fields):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fields, delimiter="\t", extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    atomic_text(path, stream.getvalue())


def value(item, key, scale=1):
    v = item.get(key)
    if v is None or v == "":
        return "—"
    return f"{float(v) / scale:,.3f}"


def word_document(path, title, blocks):
    """Minimal OOXML report with Chinese fonts; no external package installation."""
    def p(text, style="Normal"):
        return f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr><w:r><w:t xml:space="preserve">{escape(str(text))}</w:t></w:r></w:p>'
    body = [p(title, "Title")]
    for kind, content in blocks:
        if kind == "h2":
            body.append(p(content, "Heading1"))
        elif kind == "table":
            headers, rows = content
            width = 9360 // len(headers)
            grid = ''.join(f'<w:gridCol w:w="{width}"/>' for _ in headers)
            borders = ''.join(f'<w:{edge} w:val="single" w:sz="4" w:color="D9D9D9"/>' for edge in ("top", "left", "bottom", "right", "insideH", "insideV"))
            cells = []
            for index, row in enumerate([headers, *rows]):
                row_xml = '<w:tr><w:trPr>' + ('<w:tblHeader/>' if index == 0 else '') + '<w:cantSplit/></w:trPr>'
                for cell in row:
                    fill = "DFEBF5" if index == 0 else ("F7F9FB" if index % 2 == 0 else "FFFFFF")
                    row_xml += f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/><w:vAlign w:val="center"/><w:shd w:fill="{fill}"/></w:tcPr>{p(cell, "TableText")}</w:tc>'
                cells.append(row_xml + '</w:tr>')
            body.append(f'<w:tbl><w:tblPr><w:tblW w:w="9360" w:type="dxa"/><w:tblLayout w:type="fixed"/><w:tblBorders>{borders}</w:tblBorders><w:tblCellMar><w:top w:w="100" w:type="dxa"/><w:bottom w:w="100" w:type="dxa"/><w:left w:w="100" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>{grid}</w:tblGrid>{"".join(cells)}</w:tbl>')
            body.append(p(""))
        elif kind == "code":
            body.extend(p(line, "Code") for line in content.splitlines())
        else:
            body.append(p(content))
    body.append('<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1080" w:right="1440" w:bottom="1080" w:left="1440"/></w:sectPr>')
    document = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>' + ''.join(body) + '</w:body></w:document>'
    styles = '''<?xml version="1.0" encoding="UTF-8"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="Microsoft YaHei"/><w:sz w:val="22"/><w:color w:val="000000"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="140" w:line="290" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style><w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:after="240"/></w:pPr><w:rPr><w:b/><w:sz w:val="36"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="260" w:after="140"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:sz w:val="28"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="TableText"><w:name w:val="Table Text"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="40" w:line="260" w:lineRule="auto"/></w:pPr><w:rPr><w:sz w:val="20"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Code"><w:name w:val="Code"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="20"/></w:pPr><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/><w:sz w:val="18"/></w:rPr></w:style></w:styles>'''
    path = Path(path)
    tmp = path.with_name(path.name + ".partial")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr("word/document.xml", document)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/_rels/document.xml.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
    os.replace(tmp, path)


def render_documents(root, title, blocks, basename):
    html_parts = [f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>{STYLE}</style><body><h1>{html.escape(title)}</h1>']
    md = ["# " + title, ""]
    for kind, content in blocks:
        if kind == "table":
            headers, rows = content
            html_parts.append("<table><thead><tr>" + ''.join(f"<th>{html.escape(str(c))}</th>" for c in headers) + "</tr></thead><tbody>")
            for row in rows:
                html_parts.append("<tr>" + ''.join(f"<td>{html.escape(str(c))}</td>" for c in row) + "</tr>")
            html_parts.append("</tbody></table>")
            def safe(c):
                return str(c).replace("|", "\\|").replace("\n", " ")
            md += ["| " + " | ".join(map(safe, headers)) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
            md += ["| " + " | ".join(map(safe, row)) + " |" for row in rows]
        elif kind == "code":
            html_parts.append("<pre>" + html.escape(content) + "</pre>")
            md += ["```bash", content, "```"]
        else:
            tag = "h2" if kind == "h2" else "p"
            html_parts.append(f"<{tag}>{html.escape(str(content))}</{tag}>")
            md.append(("## " if kind == "h2" else "") + str(content))
        md.append("")
    html_parts.append("</body></html>")
    atomic_text(Path(root) / (basename + ".html"), "\n".join(html_parts))
    atomic_text(Path(root) / (basename + ".md"), "\n".join(md))
    word_document(Path(root) / (basename + ".docx"), title, blocks)


def build_report(root):
    root = Path(root)
    experiment = json.loads((root / "metadata/experiment.json").read_text(encoding="utf-8"))
    attempts = []
    stages = []
    for path in sorted((root / "results").glob("*/rep_*/attempt_*/result.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        # Never present a crash-left RUNNING marker as success.
        if row["status"] == "RUNNING":
            row["status"] = "INCOMPLETE"
        attempts.append(row)
        for metric_path in sorted((path.parent / "logs").glob("*.metrics.json")):
            m = json.loads(metric_path.read_text(encoding="utf-8"))
            stages.append({"sequences": row["sequences"], "repeat": row["repeat"], "attempt": row["attempt"], **m})
    attempts.sort(key=lambda r: (r["sequences"], r["repeat"], r["attempt"]))
    selected = []
    for n in experiment["sizes"]:
        for rep in range(1, experiment["repeats"] + 1):
            candidates = [r for r in attempts if r["sequences"] == n and r["repeat"] == rep]
            successful = [r for r in candidates if r["status"] == "SUCCESS"]
            if successful:
                selected.append(successful[-1])
            elif candidates:
                selected.append(candidates[-1])
            else:
                status = "SKIPPED_INSUFFICIENT_INPUT" if n > experiment["dataset"]["total_sequences"] else "NOT_RUN"
                selected.append({"sequences": n, "repeat": rep, "status": status})
    fields = ["sequences", "repeat", "attempt", "status", "started_utc", "ended_utc", "cores",
              "workflow_seconds", "attempt_seconds", "gzip_seconds", "split_seconds", "mashtree_seconds",
              "rename_seconds", "mafft_seconds", "panman_seconds", "workflow_gnu_maxrss_kib",
              "workflow_sampled_tree_peak_rss_mib", "fasta_bytes", "gzip_bytes", "alignment_bytes",
              "tree_bytes", "panman_bytes", "alignment_length", "fasta_to_panman_ratio",
              "gzip_to_panman_ratio", "alignment_to_panman_ratio", "exit_code", "failure_reason", "run_directory"]
    tsv(root / "benchmark_summary.tsv", selected, fields)
    tsv(root / "all_attempts.tsv", attempts, fields)
    tsv(root / "stage_metrics.tsv", stages, ["sequences", "repeat", "attempt", "stage", "exit_code",
        "elapsed_seconds", "gnu_wall_seconds", "gnu_user_seconds", "gnu_system_seconds", "gnu_maxrss_kib",
        "sampled_tree_peak_rss_bytes", "samples", "sample_seconds", "started_utc", "ended_utc"])
    aggregate = []
    for n in experiment["sizes"]:
        good = [r for r in selected if r["sequences"] == n and r["status"] == "SUCCESS"]
        row = {"sequences": n, "successful_repeats": len(good)}
        if good:
            times = [r["workflow_seconds"] for r in good]
            row.update(median_workflow_seconds=statistics.median(times), min_workflow_seconds=min(times),
                       max_workflow_seconds=max(times))
        aggregate.append(row)
    tsv(root / "aggregate.tsv", aggregate, ["sequences", "successful_repeats", "median_workflow_seconds", "min_workflow_seconds", "max_workflow_seconds"])
    success = sum(r["status"] == "SUCCESS" for r in selected)
    blocks = [
        ("p", f"计划运行 {len(selected)} 组，其中 {success} 组记录为成功。数据规模为 {experiment['sizes']}，每规模重复 {experiment['repeats']} 次，线程预算为 {experiment['cores']}。未运行、失败和输入不足均单独标记。"),
        ("p", "本报告由实际运行记录生成。成功要求各阶段退出正常、输出非空、比对去除 gap 后与输入一致、树叶数量及名称匹配。尚未进行 PanMAN 解码回原始序列的往返验证，因此不能据此宣称无损压缩验证完成。"),
        ("h2", "输入与实验范围"),
        ("p", f"原始输入 {experiment['input']}，共 {experiment['dataset']['total_sequences']} 条序列。输入 SHA256 为 {experiment['fingerprint']['input_sha256']}。"),
        ("p", "每个规模取原始文件前 N 条，构成嵌套子集；不随机抽样、不去重、不调整序列方向。子集重新写为每条两行的 FASTA，压缩基线使用这一份相同输入。结果只代表该顺序和数据组成。"),
        ("h2", "运行状态与耗时"),
        ("table", (["序列数", "重复", "状态", "流程秒", "PanMAN 秒"],
                   [[r['sequences'], r['repeat'], r['status'], value(r,'workflow_seconds'), value(r,'panman_seconds')] for r in selected])),
        ("h2", "内存记录"),
        ("table", (["序列数", "重复", "GNU RSS KiB", "采样进程树 RSS MiB"],
                   [[r['sequences'], r['repeat'], value(r,'workflow_gnu_maxrss_kib'), value(r,'workflow_sampled_tree_peak_rss_mib')] for r in selected])),
        ("p", "GNU time 的最大 RSS 与每隔固定时间对父子进程 RSS 求和得到的最大值分别保存。后者可能重复计算共享页，也可能漏掉采样间隔内的瞬时峰值；两者均不等同于整台机器的精确峰值内存。资源时间序列位于各尝试目录的 logs/*.resources.tsv。"),
        ("h2", "文件大小与体积比"),
        ("table", (["序列数", "重复", "FASTA MiB", "gzip MiB", "PanMAN MiB"],
                   [[r['sequences'], r['repeat'], value(r,'fasta_bytes',1048576), value(r,'gzip_bytes',1048576), value(r,'panman_bytes',1048576)] for r in selected])),
        ("table", (["序列数", "重复", "FASTA 除以 PanMAN", "gzip 除以 PanMAN"],
                   [[r['sequences'], r['repeat'], value(r,'fasta_to_panman_ratio'), value(r,'gzip_to_panman_ratio')] for r in selected])),
        ("p", "比值大于 1 表示 PanMAN 文件更小。该比较是存储体积比较；FASTA、带 gap 的比对、gzip 和 PanMAN 的表示及元数据不同。gzip 使用 -n -9。字节原值、树及比对文件大小保存在 TSV 中。"),
        ("h2", "测量口径"),
        ("p", "workflow_seconds 从启动 Conda 和 Snakemake 到其退出，包含拆分、MashTree、树名称恢复、MAFFT、PanMAN 和这些步骤的启动开销；不包含子集构建、gzip、产物校验及报告生成。attempt_seconds 另含本次 gzip 和输出校验，但不含子集复制及末尾报告生成。各阶段单独保留 wall time、CPU 用户态和内核态时间、GNU RSS、退出码与完整命令。"),
        ("p", "MAFFT 使用 --auto --thread CORES --threadit 0，自动策略可能随输入规模变化。CORES 是调度预算，不保证每个工具持续占用该数量的核。实验按规模递增串行运行，不清空操作系统文件缓存。重复次数为 1 时只能报告单次测量，不能用于估计运行波动。"),
        ("h2", "结果路径与追溯"),
        ("p", "每次尝试保存在 results/序列数/rep_编号/attempt_编号 下，最终文件为 panman/out.panman；同目录保留 input.fasta、input.fasta.gz、output/mafft.aln、output/mashtree.nwk、validation.json、checksums.json、config.json 和 logs。所有尝试均保留，不删除原始工作流结果。"),
        ("p", "benchmark_summary.tsv 选用每个规模和重复的最近成功记录；没有成功记录时保留最新失败或未完成状态。all_attempts.tsv 包含全部尝试。aggregate.tsv 只统计成功重复的流程时间。metadata 记录三套 Conda 包清单、软件版本、硬件、原始工作流和实验代码快照。"),
    ]
    failed = [r for r in selected if r.get("failure_reason")]
    for r in failed:
        blocks.append(("p", f"失败记录 n={r['sequences']} rep={r['repeat']}：{r['failure_reason']}。目录：{r.get('run_directory','')}"))
    render_documents(root, "人类线粒体 PanMAN 万条序列实验报告", blocks, "experiment_report")
    return selected
