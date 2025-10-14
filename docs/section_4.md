# Section 4: Reference Example

**Purpose**: A complete end-to-end example applying the principles and specifications.

**Input (compile_task XML)**:

```xml
<compile_task>
  <task_id>f6aff7b2-f23f-441f-b1e9-0b1e64055475</task_id>
  
  <code_context>
from dataclasses import dataclass
from typing import List, Literal

@dataclass
class CustomerFeedback:
    customer_id: str
    feedback_text: str
    product_category: str
    submission_date: str

@dataclass
class ActionItem:
    priority: Literal['high', 'medium', 'low']
    description: str
    department: str

@dataclass
class FeedbackAnalysis:
    sentiment: Literal['positive', 'neutral', 'negative']
    key_issues: List[str]
    customer_satisfaction_score: int  # 1-10
    recommended_actions: List[ActionItem]

class CustomerServiceAnalyzer:
    """
    Analyze customer feedback to extract insights and recommend actions.
    """
    
    def analyze_feedback(self, feedback: CustomerFeedback) -> FeedbackAnalysis:
        """
        Analyze customer feedback to identify sentiment, key issues, 
        and recommend appropriate follow-up actions.
        
        @compile: use XML tags for structured data presentation in user prompt
        """
        # Semantic call site - analysis delegated to LLM
        analysis: FeedbackAnalysis = analyze(feedback=feedback)
        return analysis
  </code_context>
  
  <semantic_call_site>
    <location>
      <line_number>36</line_number>
      <method_name>analyze</method_name>
    </location>
    
    <parameter_spec>
      <positional></positional>
      <keyword>
        <param name="feedback" type="CustomerFeedback" />
      </keyword>
    </parameter_spec>
    
    <return_specification>
      <type>FeedbackAnalysis</type>
      <json_schema>
{
  "type": "object",
  "properties": {
    "sentiment": {
      "type": "string",
      "enum": ["positive", "neutral", "negative"]
    },
    "key_issues": {
      "type": "array",
      "items": {"type": "string"}
    },
    "customer_satisfaction_score": {
      "type": "integer",
      "minimum": 1,
      "maximum": 10
    },
    "recommended_actions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "priority": {
            "type": "string",
            "enum": ["high", "medium", "low"]
          },
          "description": {"type": "string"},
          "department": {"type": "string"}
        },
        "required": ["priority", "description", "department"]
      }
    }
  },
  "required": ["sentiment", "key_issues", "customer_satisfaction_score", "recommended_actions"]
}
      </json_schema>
    </return_specification>
  </semantic_call_site>
</compile_task>
```

**Output (compilation result)**:

```
==f6aff7b2-f23f-441f-b1e9-0b1e64055475==SYSTEM_PROMPT==
You are a customer service analysis specialist. Your role is to analyze customer feedback to extract actionable insights that help businesses improve their service and products.

Your task is to examine customer feedback submissions and produce a comprehensive analysis that includes:
1. The overall sentiment expressed in the feedback
2. Key issues or concerns raised by the customer
3. An assessment of customer satisfaction on a 1-10 scale
4. Specific recommended actions for follow-up, prioritized by urgency

When analyzing feedback, consider the context of the product category and look for both explicit statements and implicit signals about customer experience. Your recommended actions should be practical, specific, and assigned to appropriate departments (e.g., customer service, product team, quality assurance).

Guidelines:
- Assess sentiment as positive, neutral, or negative based on the overall tone and content
- Identify distinct issues rather than repeating similar concerns
- Base the satisfaction score on the intensity and nature of feedback
- Recommend actions that directly address identified issues
- Prioritize actions as high (urgent/critical), medium (important), or low (nice-to-have)
- Assign actions to the most appropriate department for execution

Output Requirements:
Your response must be a single-line minified JSON object that strictly conforms to the following schema:

{
  "type": "object",
  "properties": {
    "sentiment": {
      "type": "string",
      "enum": ["positive", "neutral", "negative"]
    },
    "key_issues": {
      "type": "array",
      "items": {"type": "string"}
    },
    "customer_satisfaction_score": {
      "type": "integer",
      "minimum": 1,
      "maximum": 10
    },
    "recommended_actions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "priority": {
            "type": "string",
            "enum": ["high", "medium", "low"]
          },
          "description": {"type": "string"},
          "department": {"type": "string"}
        },
        "required": ["priority", "description", "department"]
      }
    }
  },
  "required": ["sentiment", "key_issues", "customer_satisfaction_score", "recommended_actions"]
}

Ensure all strings are properly escaped. Do not use pretty-printing.

Example output:
{"sentiment":"negative","key_issues":["Product arrived damaged","Poor packaging quality","Delayed response from support"],"customer_satisfaction_score":3,"recommended_actions":[{"priority":"high","description":"Contact customer immediately to arrange replacement","department":"customer service"},{"priority":"medium","description":"Review packaging standards for this product category","department":"quality assurance"}]}
==f6aff7b2-f23f-441f-b1e9-0b1e64055475==END_SYSTEM_PROMPT==
==f6aff7b2-f23f-441f-b1e9-0b1e64055475==USER_PROMPT==
Analyze the following customer feedback:

<feedback>
  <customer_id>{{feedback.customer_id}}</customer_id>
  <product_category>{{feedback.product_category}}</product_category>
  <submission_date>{{feedback.submission_date}}</submission_date>
  <feedback_text>{{feedback.feedback_text}}</feedback_text>
</feedback>

Please provide a comprehensive analysis including sentiment assessment, key issues identification, satisfaction scoring, and recommended follow-up actions.
==f6aff7b2-f23f-441f-b1e9-0b1e64055475==END_USER_PROMPT==
==f6aff7b2-f23f-441f-b1e9-0b1e64055475==NOTES==
Compilation Decisions:

1. Role Definition: Inferred from class name and docstring; phrased without exposing code symbols.
2. Compiler Directive: Applied XML wrapping per `@compile` directive in the docstring.
3. Parameter Presentation: Structured object presented in XML with explicit fields.
4. Type Inference: Parameter/return types and nested types align with schema.
5. Schema Handling: Used given precise schema; placed in SYSTEM_PROMPT; included example.
6. Output Structure: Captures nested list of objects per schema.
7. Abstraction: Hidden code structure; exposed schema field names and domain terms.
8. Guidelines: Derived from docstring and schema fields.
9. Satisfaction Score Range: Enforced by schema (1–10).
10. Action Prioritization: Matches enum; guidance given.
11. No Conflicts: Signals consistent.
==f6aff7b2-f23f-441f-b1e9-0b1e64055475==END_NOTES==

**Observations**:

- Semantic extraction: domain (customer service), intent (sentiment/issues/actions), types guide outputs.
- Abstraction applied: hide code structure; expose output fields; use domain language.
- Compiler directive: XML tags applied in user prompt per directive.
- Parameter reference protocol: dot-notation placeholders; no prohibited patterns.
- Completeness: self-contained system prompt; example shows nested structure; expectations clear.
- Quality verification: role without code exposure ✓; focus on intent ✓; placeholders valid ✓; output matches return spec ✓; guidance actionable ✓; no unsupported assumptions ✓; decisions recorded ✓