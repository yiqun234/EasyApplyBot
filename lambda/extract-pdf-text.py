import json
import os
import base64
import tempfile
from openai import OpenAI


def lambda_handler(event, context):
    """
    Lambda函数，用于使用OpenAI API提取PDF文件中的文本内容

    请求格式:
    {
        "pdf_filename": "简历文件名.pdf",
        "pdf_base64": "Base64编码的PDF文件内容",
        "openai_api_key": "用户的OpenAI API密钥（可选）"
    }

    响应格式:
    {
        "extracted_text": "提取的文本内容",
        "status": "success"
    }
    """
    try:
        # 解析请求内容
        if 'pdf_base64' in event:
            user_api_key = event.get('openai_api_key', None)
            pdf_filename = event.get('pdf_filename', 'document.pdf')
            pdf_base64 = event.get('pdf_base64', '')

        elif 'body' in event:
            body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event.get('body', {})
            user_api_key = body.get('openai_api_key', None)
            pdf_filename = body.get('pdf_filename', 'document.pdf')
            pdf_base64 = body.get('pdf_base64', '')

        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': '找不到请求参数',
                    'event': event
                })
            }

        # 从环境变量获取API密钥
        api_key = user_api_key or os.environ.get('OPENAI_API_KEY')
        if not api_key:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'OpenAI API密钥未配置'
                })
            }

        # 验证必需参数
        if not pdf_base64:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': '缺少PDF文件内容（pdf_base64）'
                })
            }

        # 初始化OpenAI客户端
        openai_client = OpenAI(api_key=api_key)

        # # 解码Base64数据并临时保存为文件
        # pdf_data = base64.b64decode(pdf_base64)

        # with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        #     temp_path = temp_file.name
        #     temp_file.write(pdf_data)

        # # 上传临时文件到OpenAI
        # with open(temp_path, 'rb') as f:
        #     file = openai_client.files.create(
        #         file=f,
        #         purpose="user_data"
        #     )

        try:
            # 使用OpenAI的Responses API提取PDF文本
            response = openai_client.responses.create(
                model="gpt-4.1-mini",
                input=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_file",
                                "filename": pdf_filename,
                                "file_data": f"data:application/pdf;base64,{pdf_base64}",
                            },
                            {
                                "type": "input_text",
                                "text": "提取此PDF文件中的所有文本内容。只返回提取的文本，不要添加任何评论或分析。",
                            },
                        ]
                    }
                ]
            )

            # 提取文本
            extracted_text = ""
            if hasattr(response, 'output_text') and response.output_text:
                extracted_text = response.output_text.strip()
            else:
                extracted_text = "无法提取文本，请检查PDF文件"

            # 返回成功响应
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'extracted_text': extracted_text,
                    'status': 'success'
                })
            }

        finally:
            # 清理：删除临时文件和已上传的文件
            try:
                os.unlink(temp_path)
            except:
                pass

            try:
                openai_client.files.delete(file.id)
            except:
                pass

    except Exception as e:
        # 错误处理
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'status': 'error'
            })
        } 