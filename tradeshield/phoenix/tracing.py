"""
Phoenix Tracing Setup

Connects OpenInference instrumentation to Arize Phoenix Cloud.
Every ADK agent action (Gemini calls, tool invocations, responses)
is automatically captured and sent to Phoenix as traces.

This file runs ONCE at startup. After that, tracing is automatic.

How it works:
1. Sets Phoenix Cloud credentials from environment variables
2. Calls register() which sets up the OpenTelemetry pipeline
3. auto_instrument=True detects installed instrumentors (ADK, GenAI)
4. Every subsequent ADK operation is traced without manual code

Source: https://google.github.io/adk-docs/observability/phoenix/
Source: https://arize.com/docs/phoenix/integrations/python/google-adk/google-adk-tracing
"""

import os
from tradeshield.config import PHOENIX_API_KEY, PHOENIX_COLLECTOR_ENDPOINT


def setup_tracing():
    """
    Initialize Phoenix Cloud tracing for the TradeShield agent.

    Must be called BEFORE creating the ADK agent.
    Sets environment variables and registers the tracer provider.

    Returns:
        tracer_provider: The configured OpenTelemetry tracer provider.
    """
    # Phoenix Cloud requires these environment variables
    # They tell the OpenTelemetry exporter WHERE to send traces
    # and HOW to authenticate
    os.environ["PHOENIX_CLIENT_HEADERS"] = f"api_key={PHOENIX_API_KEY}"
    os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = PHOENIX_COLLECTOR_ENDPOINT

    # Import here (after env vars are set) to avoid import-time issues
    from phoenix.otel import register

    # register() does three things:
    # 1. Creates an OpenTelemetry TracerProvider
    # 2. Configures an OTLP exporter pointing to Phoenix Cloud
    # 3. With auto_instrument=True, finds and activates all installed
    #    OpenInference instrumentors (ADK, GenAI)
    tracer_provider = register(
        project_name="tradeshield",  # Shows as project name in Phoenix dashboard
        auto_instrument=True,         # Auto-detect ADK + GenAI instrumentors
    )

    print("[TradeShield] Phoenix tracing initialized")
    print(f"[TradeShield] Traces → {PHOENIX_COLLECTOR_ENDPOINT}")

    return tracer_provider
