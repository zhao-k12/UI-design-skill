"""Penpot entry point for independent primitive and linked-copy content QA."""
from adapters.section_content_qa import verify as verify_native


def verify(execution,patch,before,after,request,*,visual_review=None):
    return verify_native(execution,patch,before,after,request,visual_review=visual_review,platform='penpot')
