# Section 4: Reference Example

This section provides a complete end-to-end example demonstrating the application of all principles and specifications from the previous sections.

## 4.1 Input: Compilation Task

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

## 4.2 Output: Compilation Result

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

1. Role Definition: Inferred from class name "CustomerServiceAnalyzer" and method docstring. Chose "customer service analysis specialist" to convey expertise without exposing the class name.

2. Compiler Directive: Found "@compile: use XML tags for structured data presentation in user prompt" on line 34. Applied by wrapping the feedback parameter in XML structure with individual fields.

3. Parameter Presentation: The feedback parameter is a structured object (CustomerFeedback). Used XML format as directed, with explicit field tags for clarity. This makes the structure readable for the runtime LLM while following the directive.

4. Type Inference: 
   - Parameter type inferred from method signature: feedback: CustomerFeedback
   - Return type inferred from method signature: FeedbackAnalysis
   - All nested types (ActionItem) fully analyzed from the JSON schema

5. Schema Handling:
   - Input schema was precise and complete, so used it as-is without refinement
   - Placed schema in SYSTEM_PROMPT under "Output Requirements" section
   - This is appropriate because the output structure is task-invariant (same schema for all feedback analysis)
   - Included both the formal JSON Schema and a concrete example for clarity
   - Schema placement in SYSTEM_PROMPT allows the runtime LLM to internalize the structure before seeing specific data

6. Output Structure: The return type has nested complexity (list of ActionItem objects). Provided the complete JSON Schema to precisely define the structure, followed by a concrete example showing the full nested structure.

7. Abstraction: 
   - Hidden: "CustomerServiceAnalyzer" class name, "analyze_feedback" method name
   - Exposed: Field names from JSON schema (sentiment, key_issues, etc.) as these are part of the output contract
   - Used business domain language throughout (customer, feedback, analysis, recommendations)

8. Guidelines: Derived from the method docstring ("identify sentiment, key issues, and recommend appropriate follow-up actions") and expanded based on the return type structure. Each output field has corresponding guidance.

9. Satisfaction Score Range: Noted from the comment "# 1-10" in the code and enforced in the JSON schema (minimum: 1, maximum: 10). Included in guidelines.

10. Action Prioritization: The ActionItem type includes a priority field with three levels. Provided clear guidance on how to assign priority levels in the system prompt.

11. No Conflicts: All signals (types, comments, docstring, directive) were consistent. The directive was straightforward to apply.
==f6aff7b2-f23f-441f-b1e9-0b1e64055475==END_NOTES==
```

## 4.3 Key Observations

### Semantic Extraction
- **Business domain** identified from class name and docstrings: customer service analysis
- **Intent** extracted from method docstring: analyze feedback for sentiment, issues, and actions
- **Type structure** provided clear guidance on required output fields

### Abstraction Applied
- **Hidden**: Code structure (class name `CustomerServiceAnalyzer`, method name `analyze_feedback`)
- **Exposed**: Output contract fields (`sentiment`, `key_issues`, `recommended_actions`)
- **Language**: Business domain terminology (customer, feedback, satisfaction) rather than programming terms

### Compiler Directive
- Directive `@compile: use XML tags for structured data presentation` was found and applied
- Parameter presentation changed from simple format to XML-wrapped structure
- This demonstrates how directives override default presentation strategies

### Parameter Reference Protocol
- Used `{{feedback.customer_id}}`, `{{feedback.feedback_text}}` etc. with dot notation
- Followed valid placeholder syntax throughout
- No prohibited patterns (subscripts, expressions, method calls)

### Completeness
- System prompt is self-contained: runtime LLM doesn't need to see the original code
- All output fields have corresponding guidance
- Example output demonstrates the complete nested structure
- Task is fully specified with clear expectations

### Quality Verification
- Role defined without code exposure ✓
- Task focuses on intent, not implementation ✓
- Valid placeholder syntax used ✓
- Output requirements match return specification ✓
- Guidelines address execution, not formatting ✓
- No unsupported assumptions introduced ✓
- Decisions documented in NOTES ✓