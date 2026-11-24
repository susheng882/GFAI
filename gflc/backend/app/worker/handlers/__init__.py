# -*- coding: utf-8 -*-
"""后台任务处理逻辑（T-3 按任务类型拆分）。

所有重活在此执行，进度通过 update 回写。
对外接口与原单文件 handlers.py 完全一致：调用方仍可
`from app.worker.handlers import register_all, handle_pdf_parse, ...`。
"""
from app.worker import runner
from app.worker.handlers.common import _cp_get, _cp_save, _ts_mmss
from app.worker.handlers.dashboard import _dash_facts, handle_dashboard_generate
from app.worker.handlers.parse import (_SUBJECT_KEYS, _file_hash, _import_document,
                                       _infer_subject, handle_card_generate,
                                       handle_pdf_parse, handle_question_import)
from app.worker.handlers.plan import handle_plan_generate
from app.worker.handlers.video import (_RENDER, _TPL_NAME, _TPL_SCHEMA, _VIDEO_SUFFIX,
                                       _VOutline, _VOutlineLeaf, _VOutlineSection, _VQa,
                                       _VQaItem, _VSummary, _append_sources, _dedupe_frames,
                                       _frames_ocr_enabled, _is_video_src, _note_points,
                                       _render_outline_md, _render_qa_md,
                                       _render_summary_md, _replace_old_note,
                                       _rehydrate_source, _reuse_material_by_url,
                                       _transcriber_mode, _try_bcut, _video_pipeline,
                                       handle_video_upload, handle_video_url)


def register_all():
    runner.register("pdf_parse", handle_pdf_parse)
    runner.register("card_generate", handle_card_generate)
    runner.register("question_import", handle_question_import)
    runner.register("plan_generate", handle_plan_generate)
    runner.register("video_upload", handle_video_upload)
    runner.register("video_url", handle_video_url)
    runner.register("dashboard_generate", handle_dashboard_generate)
