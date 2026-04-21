from fastapi import APIRouter
from server.models.repo import StackTraceResolveRequest, StackTraceResolveResponse
from server.core import stack_trace

router = APIRouter(tags=["stacktrace"])


@router.post("/stacktrace/resolve", response_model=StackTraceResolveResponse)
async def resolve_stack_trace(body: StackTraceResolveRequest):
    frames = stack_trace.resolve_stack_trace(body.stackTrace)
    return StackTraceResolveResponse(
        frames=frames,
        resolvedCount=sum(1 for f in frames if f.resolved),
        totalCount=len(frames),
    )


@router.post("/stacktrace/callpath", response_model=StackTraceResolveResponse)
async def callpath(body: StackTraceResolveRequest):
    # Same resolve logic; frames are returned in order top → bottom, which is the call path
    frames = stack_trace.resolve_stack_trace(body.stackTrace)
    return StackTraceResolveResponse(
        frames=frames,
        resolvedCount=sum(1 for f in frames if f.resolved),
        totalCount=len(frames),
    )
