import json
import os
import openai


def lambda_handler(event, context):
    """
    Lambda function to evaluate job fit for candidates

    Request format:
    {
        "context": "Personal information and resume content...",
        "job_title": "Job title",
        "job_description": "Full job description",
        "debug": false
    }

    Response format:
    {
        "result": true/false,  # true=should apply, false=should skip
        "explanation": "Evaluation explanation (optional, only returned when debug=true)",
        "status": "success"
    }
    """
    try:
        # Parse request body
        if 'job_title' in event:
            user_api_key = event.get('openai_api_key', None)
            context = event.get('context', '')
            job_title = event.get('job_title', '')
            job_description = event.get('job_description', '')
            debug = event.get('debug', False)

        elif 'body' in event:
            body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event.get('body', {})
            user_api_key = body.get('openai_api_key', None)
            context = body.get('context', '')
            job_title = body.get('job_title', '')
            job_description = body.get('job_description', '')
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
        if not job_title or not job_description:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing job title or description'
                })
            }

        # Initialize OpenAI client
        openai_client = openai.OpenAI(api_key=api_key)

        # Build system prompt
        system_prompt = """You are evaluating job fit for technical roles. 
            Recommend APPLY if:
            - Candidate meets 65 percent of the core requirements
            - Experience gap is 2 years or less
            - Has relevant transferable skills

            Return SKIP if:
            - Experience gap is greater than 2 years
            - Missing multiple core requirements
            - Role is clearly more senior
            - The role is focused on an uncommon technology or skill that is required and that the candidate does not have experience with
            - The role is a leadership role or a role that requires managing people and the candidate has no experience leading or managing people

            """

        if debug:
            system_prompt += """
            You are in debug mode. Return a detailed explanation of your reasoning for each requirement.

            Return APPLY or SKIP followed by a brief explanation.

            Format response as: APPLY/SKIP: [brief reason]"""
        else:
            system_prompt += """Return only APPLY or SKIP."""

        # Call OpenAI API
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Job: {job_title}\n{job_description}\n\nCandidate:\n{context}"}
            ],
            max_tokens=250 if debug else 1,
            temperature=0.2
        )

        answer = response.choices[0].message.content.strip()

        # Parse result
        decision = answer.upper().startswith('A')  # APPLY = True, SKIP = False
        explanation = answer if debug else ""

        # Return result
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'result': decision,
                'explanation': explanation,
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