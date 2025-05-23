# -*- coding: utf-8 -*-
# worksheet_updater.py
# -----------------------------------------------------------------------------
#  功能說明：
#  1. 讀取 analysis_results.json → KeywordAnalyzer 過濾。
#  2. 針對 **每一筆 snippet**：再次偵測引用檔案 (【編號 名稱】)。
#  3. 將結果寫入 IEC 62443-2-4 Worksheet：
#     • Conformity Statement
#     • Conformity Evidence：主文件 + "==>" 引用文件 (避免重複/自引用)。
#  4. 透過 Tkinter 讓使用者選擇輸出位置。
# -----------------------------------------------------------------------------

import json
import os
import re
import shutil
import tkinter as tk
from tkinter import filedialog

import openpyxl
from conformity_analysis_module.config import Config
from conformity_analysis_module.core.keyword_analyzer import KeywordAnalyzer
from conformity_analysis_module.utils.docx_section_extractor import DocxSectionExtractor
from conformity_analysis_module.utils.logger import logger


class WorksheetUpdater:
    """將分析結果寫入 IEC 62443-2-4 Excel 工作表。"""

    @staticmethod
    def update_worksheet():  # noqa: C901
        """執行 Worksheet 更新流程。"""

        # ------------------------------------------------------------------
        # 基本檔案檢查
        # ------------------------------------------------------------------
        analysis_file = Config.ANALYSIS_OUTPUT
        template_file = Config.WORKSHEET_FILE
        logger.info("analysis_results.json 路徑: %s", analysis_file)

        if not os.path.exists(analysis_file):
            return False, "analysis_results.json 不存在，請先執行分析"
        if not os.path.exists(template_file):
            return False, "找不到模板檔案 IEC62443_2_4d_2024-worksheet.xlsx"

        # ------------------------------------------------------------------
        # 讀取分析結果
        # ------------------------------------------------------------------
        try:
            with open(analysis_file, "r", encoding="utf-8") as fp:
                analysis_results = json.load(fp)
        except Exception:
            logger.exception("讀取 %s 時發生錯誤", analysis_file)
            return False, "讀取 analysis_results.json 時發生錯誤"

        # 建立全域 source_file 清單 (供引用偵測)
        all_source_files: list[str] = []
        for r in analysis_results:
            sf = r.get("source_file")
            if sf and sf not in all_source_files:
                all_source_files.append(sf)

        # ------------------------------------------------------------------
        # 關鍵詞過濾 & 每 snippet 引用偵測
        # ------------------------------------------------------------------
        analyzer = KeywordAnalyzer()
        enhanced = analyzer.analyze(analysis_results, min_score=2)

        ref_token = re.compile(r"【([^】]+)】")
        code_pat = re.compile(r"([A-Z]+-\d+-\d+(?:[A-Za-z])?)\s+.*")

        for res in enhanced:
            snippet = res.get("snippet", "")
            refs: list[str] = []
            for token in ref_token.findall(snippet):
                m = code_pat.match(token)
                if not m:
                    continue
                ref_code = m.group(1)
                base_code = re.sub(r"([A-Z]+-\d+-\d+)[A-Za-z]?", r"\1", ref_code)
                for sf in all_source_files:
                    stem = os.path.splitext(os.path.basename(sf))[0]
                    if ref_code in stem or base_code in stem:
                        refs.append(sf)
                        break
            res["referenced_files"] = refs

        # 統計
        total, accept = len(analysis_results), len(enhanced)
        reject = total - accept
        rej_rate = reject / total if total else 0
        logger.info(
            "關鍵詞分析: %d → 接受 %d, 拒絕 %d (%.2f%%)", total, accept, reject, rej_rate * 100
        )

        # ------------------------------------------------------------------
        # 複製模板
        # ------------------------------------------------------------------
        tmp_dir = os.path.join(Config.ROOT_DIR, "temp")
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_file = os.path.join(tmp_dir, "IEC62443_2_4d_filled.xlsx")
        shutil.copy(template_file, tmp_file)

        wb = openpyxl.load_workbook(tmp_file)
        ws = wb.active

        header = {
            str(ws.cell(row=1, column=c).value).strip().lower(): c
            for c in range(1, ws.max_column + 1)
            if ws.cell(row=1, column=c).value
        }
        id_col, stmt_col, evi_col = (
            header[h] for h in ("iec 62443-2-4 id", "conformity statement", "conformity evidence")
        )

        norm = lambda s: re.sub(r"\s+", "", str(s).upper())

        # 分組 by requirement
        by_req: dict[str, list[dict]] = {}
        for r in enhanced:
            req = norm(r.get("requirement", ""))
            by_req.setdefault(req, []).append(r)

        # ------------------------------------------------------------------
        # 寫入 Excel
        # ------------------------------------------------------------------
        for row in range(2, ws.max_row + 1):
            req_id = norm(ws.cell(row=row, column=id_col).value)
            if req_id not in by_req:
                continue

            entries = by_req[req_id]

            # ---------- Conformity Statement ----------
            stmt_cells: list[str] = []
            for ent in entries:
                src_name = os.path.basename(ent["source_file"])
                snippet = ent["snippet"]
                score = ent.get("keyword_score", 0)
                kw = ", ".join(ent.get("matched_keywords", []))
                section_no = ""
                if src_name.lower().endswith(".docx"):
                    try:
                        section_no = DocxSectionExtractor(ent["source_file"]).get_section_number(snippet)
                    except Exception:
                        section_no = "(無編號)"
                stmt_cells.append(
                    f"{src_name}\n Section {section_no} described that {snippet}\n[關鍵詞分數: {score}, 匹配關鍵詞: {kw}]"
                )
            ws.cell(row=row, column=stmt_col, value="\n\n".join(stmt_cells))

            # ---------- Conformity Evidence ----------
            evidence_texts: list[str] = []
            handled_main_docs: set[str] = set()  # 追蹤已處理的主文件
            all_ref_docs: set[str] = set()  # 追蹤所有被引用的文件
            doc_with_refs: dict[str, set[str]] = {}  # 每個主文件及其所有引用

            # 第一遍：收集所有主文件及其引用關係
            for ent in entries:
                src_base = os.path.basename(ent["source_file"])
                src_name = os.path.splitext(src_base)[0]
                
                # 初始化這個文件的引用集合
                if src_name not in doc_with_refs:
                    doc_with_refs[src_name] = set()
                
                # 添加所有引用
                for rf in ent["referenced_files"]:
                    rf_base = os.path.basename(rf)
                    rf_name = os.path.splitext(rf_base)[0]
                    
                    # 不添加自引用
                    if src_base != rf_base:
                        doc_with_refs[src_name].add(rf_name)
                        all_ref_docs.add(rf_name)  # 標記為被引用文檔

            # 第二遍：構建結果文本
            # 先處理有snippet的主文件
            for ent in entries:
                src_base = os.path.basename(ent["source_file"])
                src_name = os.path.splitext(src_base)[0]
                
                # 如果這個主文件已經處理過，跳過
                if src_name in handled_main_docs:
                    continue
                
                # 添加主文件及其引用
                text = src_name
                if src_name in doc_with_refs:
                    for ref_name in sorted(doc_with_refs[src_name]):
                        text += f"\n==> {ref_name}"
                
                evidence_texts.append(text)
                handled_main_docs.add(src_name)

            # 只添加那些有自己snippet但沒有被處理過的文檔
            for ent in entries:
                src_base = os.path.basename(ent["source_file"])
                src_name = os.path.splitext(src_base)[0]
                
                if src_name not in handled_main_docs:
                    evidence_texts.append(src_name)
                    handled_main_docs.add(src_name)

            ws.cell(row=row, column=evi_col, value="\n\n".join(evidence_texts))

        # ------------------------------------------------------------------
        # 儲存
        # ------------------------------------------------------------------
        root = tk.Tk()
        root.withdraw()
        save = filedialog.asksaveasfilename(
            title="選擇儲存 Excel 檔案",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="IEC62443_2_4d_filled.xlsx",
        )
        if not save:
            logger.warning("使用者取消存檔")
            return False, "使用者取消存檔"

        wb.save(save)
        logger.info("Worksheet 更新完成，已儲存至 %s", save)
        return (
            True,
            f"Worksheet 更新完成，檔案已儲存至 {save}\n"
            f"關鍵詞分析：接受 {accept} 筆, 拒絕 {reject} 筆 ({rej_rate * 100:.2f}%)",
        )
