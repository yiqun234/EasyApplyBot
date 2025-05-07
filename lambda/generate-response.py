import json
import os
import re
import openai


def lambda_handler(event, context):
    """
    Lambda function to handle AI response generation

    Request format:
    {
        "context": "Personal information and resume content...",
        "question": "Application question",
        "response_type": "text/numeric/choice",
        "options": [Optional for choice type, list of options],
        "max_tokens": 3000,
        "debug": false
    }

    Response format:
    {
        "result": "Generated response",
        "status": "success"
    }
    """
    try:
        if 'question' in event:
            user_api_key = event.get('openai_api_key', None)
            context = event.get('context', '')
            question_text = event.get('question', '')
            response_type = event.get('response_type', 'text')
            options = event.get('options', None)
            max_tokens = int(event.get('max_tokens', 3000))
            debug = event.get('debug', False)

        elif 'body' in event:
            body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event.get('body', {})
            user_api_key = body.get('openai_api_key', None)
            context = body.get('context', '')
            question_text = body.get('question', '')
            response_type = body.get('response_type', 'text')
            options = body.get('options', None)
            max_tokens = int(body.get('max_tokens', 3000))
            debug = body.get('debug', False)

        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Could not find parameters in request',
                    'event': event
                })
            }

        # Get API key from environment variables
        api_key = user_api_key or os.environ.get('OPENAI_API_KEY')
        if not api_key:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'OpenAI API key not configured'
                })
            }

        # Validate required parameters
        if not question_text:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing question parameter'
                })
            }

        # Initialize OpenAI client
        openai_client = openai.OpenAI(api_key=api_key)

        # Build system prompt based on response type
        system_prompt = {
            "text": """
You are an intelligent AI assistant filling out a form and answer like human,. 
Respond concisely based on the type of question:

1. If the question asks for **years of experience, duration, or numeric value**, return **only a number** (e.g., "2", "5", "10").
2. If the question is **a Yes/No question**, return **only "Yes" or "No"**.
3. If the question requires a **short description**, give a **single-sentence response**.
4. If the question requires a **detailed response**, provide a **well-structured and human-like answer and keep no of character <350 for answering**.
5. Do **not** repeat the question in your answer.
6. here is user information to answer the questions if needed:
**User Information:** 
{}
""",
            "numeric": "You are a helpful assistant providing numeric answers to job application questions. Based on the candidate's experience, provide a single number as your response. No explanation needed.",
            "choice": """"
                You are a helpful assistant selecting the most appropriate answer choice for job application questions. Based on the candidate's background, select the best option by returning only its index number. 

Important rules:
1. Never select options like "Select an option" or other placeholder instructions
2. Only select "Yes" for questions when you have explicit evidence supporting that answer
3. When in doubt about factual information not provided in context, default to the most conservative or non-committal valid option
4. You need to think carefully, but in the end you need to return the option number.
                """
        }[response_type]

        if response_type == "text":
            system_prompt = system_prompt.format(context)
            user_content = f"Please answer this job application question: {question_text}"
        else:
            user_content = f"Using this candidate's background and resume:\n{context}\n\nPlease answer this job application question: {question_text}"

        if response_type == "choice" and options:
            options_text = "\n".join([f"{idx}: {text}" for idx, text in options])
            user_content += f"\n\nSelect the most appropriate answer by providing its index number from these options:\n{options_text}"

        # Call OpenAI API
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )

        answer = response.choices[0].message.content.strip()

        # Process different types of responses
        if response_type == "numeric":
            # Extract first number from response
            numbers = re.findall(r'\d+', answer)
            if numbers:
                result = int(numbers[0])
            else:
                result = 0
        elif response_type == "choice":
            # Extract the index number from the response
            numbers = re.findall(r'\d+', answer)
            if numbers and options:
                index = int(numbers[0])
                # Ensure index is within valid range
                if 0 <= index < len(options):
                    result = index
                else:
                    result = None
            else:
                result = None
        else:
            result = answer

        # Return success response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'result': result,
                'status': 'success'
            })
        }

    except Exception as e:
        # Error handling
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'status': 'error'
            })
        }