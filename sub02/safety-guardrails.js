// Safety Guardrails & Model Fallback System
// 1. Checks user input for sensitive data (API keys, cards, emails)
// 2. Calls primary AI model, or falls back to backup model if it fails
// 3. Validates output to detect hallucinated citations or inappropriate advice
// 4. Logs events and maintains a review queue

import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import OpenAI from "openai";

// Models and default safe response
const PRIMARY_MODEL = process.env.OPENAI_PRIMARY_MODEL || "gpt-5.6-terra";
const FALLBACK_MODEL = process.env.OPENAI_FALLBACK_MODEL || "gpt-5.6-luna";
const SAFE_DEFAULT = "We're reviewing this with a team member. Please try again shortly.";

// System prompt telling AI to stick strictly to facts
const SYSTEM_PROMPT = `You are a careful assistant that separates sourced facts from uncertainty.
Cite only sources explicitly provided in the context.
Never invent a citation or source.
If no source is available, say that the claim cannot be sourced.
Do not present medical or legal information as professional advice.`;

// In-memory lists for logs and human review items
const securityEvents = [];
const reviewQueue = [];

// Simple sensitive patterns to watch out for
const sensitivePatterns = [
  { label: "email address", pattern: /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/i },
  { label: "possible API key", pattern: /\bsk-[A-Za-z0-9_-]{20,}\b/ },
  { label: "possible payment-card number", pattern: /\b(?:\d[ -]*?){13,19}\b/ },
];

// Helper: Log security events with a timestamp
function logSecurityEvent(type, details = {}) {
  const event = {
    timestamp: new Date().toISOString(),
    type: type,
    ...details,
  };
  securityEvents.push(event);
  return event;
}

// Helper: Add an item to the human review list
function addToReviewQueue(item) {
  const reviewItem = {
    id: reviewQueue.length + 1,
    createdAt: new Date().toISOString(),
    ...item,
  };
  reviewQueue.push(reviewItem);
  return reviewItem;
}

// Helper: Send to human review
function sendToHumanReview(item) {
  return addToReviewQueue(item);
}

// Helper: Create a fallback response object
function handleFallback(reason = "The request could not be completed safely.") {
  return {
    status: "fallback",
    answer: SAFE_DEFAULT,
    reason: reason,
  };
}

// Step 1: Validate User Input
function validateInput(input) {
  const reasons = [];

  // Check if input is valid text
  if (typeof input !== "string" || input.trim().length === 0) {
    reasons.push("Input must be a non-empty string");
    return { isValid: false, reasons: reasons };
  }

  // Check for sensitive patterns
  for (const item of sensitivePatterns) {
    if (item.pattern.test(input)) {
      reasons.push(`Illustrative pattern matched: ${item.label}`);
    }
  }

  // Check length
  if (input.length > 4000) {
    reasons.push("Input exceeds the educational example's length limit");
  }

  return {
    isValid: reasons.length === 0,
    reasons: reasons,
  };
}

// Check input and log/queue if rejected
function safeQuery(input) {
  const validation = validateInput(input);

  if (!validation.isValid) {
    logSecurityEvent("input_rejected", { reasons: validation.reasons });
    sendToHumanReview({ stage: "input", reasons: validation.reasons });
    return { ok: false, reason: validation.reasons.join("; ") };
  }

  return { ok: true, value: input.trim() };
}

// Step 2: Validate Model Output
function validateOutput(output) {
  const reasons = [];

  if (typeof output !== "string" || output.trim().length === 0) {
    return { isValid: false, reasons: ["Output must be a non-empty string"] };
  }

  // Heuristics for detecting citations, uncertainty, or risky advice
  const hasCitation = /\[[^\]]{2,}\]|https?:\/\/|\bsource:/i.test(output);
  const expressesUncertainty = /\b(may|might|uncertain|cannot verify|cannot be sourced|based on|according to)\b/i.test(output);
  const looksLikeProfessionalAdvice = /\b(you should|you must|i recommend)\b.{0,80}\b(dosage|diagnos|medication|lawsuit|legal action|plead)\b/i.test(output);

  if (looksLikeProfessionalAdvice) {
    reasons.push("Medical/legal advice detected");
  }

  if (output.length > 300 && !hasCitation) {
    reasons.push("Long claim without sources");
  }

  if (output.length > 300 && !hasCitation && !expressesUncertainty) {
    reasons.push("No uncertainty or citations");
  }

  return {
    isValid: reasons.length === 0,
    reasons: reasons,
  };
}

// Helper: Setup OpenAI client
function createOpenAIClient() {
  if (!process.env.OPENAI_API_KEY) {
    throw new Error("OPENAI_API_KEY is required for the live API example");
  }
  return new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
}

// Call the OpenAI model using the Responses API
async function requestModel(input, options = {}) {
  const context = options.context || "";
  const model = options.model;
  const client = options.client || createOpenAIClient();

  const sourceContext = context.trim()
    ? `SOURCE CONTEXT:\n${context.trim()}`
    : "SOURCE CONTEXT:\nNo source was supplied.";

  const response = await client.responses.create({
    model: model,
    instructions: SYSTEM_PROMPT,
    input: `${sourceContext}\n\nUSER QUESTION:\n${input}`,
  });

  if (!response.output_text) {
    throw new Error("The API response did not contain output_text");
  }

  return response.output_text;
}

// Call AI with input and output safety checks
async function callAIWithGuardrails(input, options = {}) {
  const context = options.context || "";
  const model = options.model || PRIMARY_MODEL;
  const client = options.client;

  // 1. Verify input
  const checkedInput = safeQuery(input);
  if (!checkedInput.ok) {
    return handleFallback(checkedInput.reason);
  }

  // 2. Send request to model
  const answer = await requestModel(checkedInput.value, {
    context: context,
    model: model,
    client: client,
  });

  // 3. Verify output
  const checkedOutput = validateOutput(answer);
  if (!checkedOutput.isValid) {
    logSecurityEvent("output_rejected", {
      model: model,
      reasons: checkedOutput.reasons,
    });
    sendToHumanReview({
      stage: "output",
      model: model,
      reasons: checkedOutput.reasons,
    });
    return handleFallback(checkedOutput.reasons.join("; "));
  }

  return { status: "ok", answer: answer, model: model };
}

// Call AI and log every start, completion, or failure
async function callAIWithLogging(input, options = {}) {
  const model = options.model || PRIMARY_MODEL;
  logSecurityEvent("model_call_started", { model: model });

  try {
    const result = await callAIWithGuardrails(input, { ...options, model: model });
    logSecurityEvent("model_call_completed", { model: model, status: result.status });
    return result;
  } catch (error) {
    logSecurityEvent("model_call_failed", { model: model, error: error.message });
    throw error;
  }
}

// Summarize failures from security events
function analyzeFailures(events = securityEvents) {
  const summary = { total: 0, byType: {} };

  for (const event of events) {
    const isFailure =
      event.type.includes("failed") ||
      event.type.includes("rejected") ||
      event.status === "fallback";

    if (isFailure) {
      summary.total += 1;
      summary.byType[event.type] = (summary.byType[event.type] || 0) + 1;
    }
  }

  return summary;
}

// Try primary model
function tryMainModel(input, options = {}) {
  return callAIWithLogging(input, { ...options, model: PRIMARY_MODEL });
}

// Try backup fallback model
function tryFallbackModel(input, options = {}) {
  return callAIWithLogging(input, { ...options, model: FALLBACK_MODEL });
}

// Return safe default if all models fail
function trySafeDefault(reason) {
  logSecurityEvent("safe_default_used", { reason: reason });
  return handleFallback(reason);
}

// Full workflow: Try Primary -> If error, Try Fallback -> If error, Return Safe Default
async function queryWithFallbacks(input, options = {}) {
  try {
    return await tryMainModel(input, options);
  } catch (mainError) {
    try {
      return await tryFallbackModel(input, options);
    } catch (fallbackError) {
      return trySafeDefault(
        `Both model attempts failed: ${mainError.message}; ${fallbackError.message}`
      );
    }
  }
}

// Run local mocked demo without paying for API calls
async function runLocalDemo() {
  let calls = 0;

  // Mock client simulating primary model outage
  const mockClient = {
    responses: {
      create: async ({ model }) => {
        calls += 1;
        if (model === PRIMARY_MODEL) {
          throw new Error("Simulated primary model outage");
        }
        return {
          output_text:
            "According to [DataMind Support Information], Pro Plan email support responds within 24 hours.",
        };
      },
    },
  };

  const result = await queryWithFallbacks("How quickly does Pro Plan support respond?", {
    context: "[DataMind Support Information] Pro Plan: Email support within 24 hours.",
    client: mockClient,
  });

  // Example of rejecting sensitive input
  safeQuery("Please contact reader@example.com with the result.");

  // Example of safe default
  const safeDefault = trySafeDefault("Demonstrating the final local fallback");

  console.log("Local mocked guardrails demo (no API calls)");
  console.log({ result, safeDefault, calls, reviewItems: reviewQueue.length });
  console.log("Failure summary:", analyzeFailures());
}

// Run live demo calling OpenAI API
async function runLiveDemo() {
  const context = await readFile(
    new URL("./data/additional_info.txt", import.meta.url),
    "utf8"
  );
  const result = await queryWithFallbacks("How quickly does Pro Plan support respond?", {
    context: `[DataMind Support Information]\n${context}`,
  });

  console.log(result);
}

// Run automatically if this file is executed directly
const isMainModule =
  process.argv[1] &&
  import.meta.url === pathToFileURL(resolve(process.argv[1])).href;

if (isMainModule) {
  const run = process.argv.includes("--live") ? runLiveDemo : runLocalDemo;
  run().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}

// Export all functions so other files can use them
export {
  SYSTEM_PROMPT,
  addToReviewQueue,
  analyzeFailures,
  callAIWithGuardrails,
  callAIWithLogging,
  handleFallback,
  logSecurityEvent,
  queryWithFallbacks,
  safeQuery,
  sendToHumanReview,
  tryFallbackModel,
  tryMainModel,
  trySafeDefault,
  validateInput,
  validateOutput,
};
