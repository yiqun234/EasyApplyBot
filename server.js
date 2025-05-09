const express = require('express');
const cors = require('cors');
const OpenAI = require('openai');
const app = express();
const port = process.env.PORT || 3000;

app.use(cors());
app.use(express.json({limit: '10mb'})); // 增加限制以处理大型简历内容

app.post('/extract-from-resume', async (req, res) => {
  try {
    const { 
      resumeText, 
      options, 
      structure,
      useProxy, 
      proxyUrl, 
      metadata 
    } = req.body;
    
    // 检查简历文本
    if (!resumeText || resumeText.trim().length === 0) {
      return res.status(400).json({ error: '简历文本内容为空' });
    }
    
    // 检查是否提供了结构定义
    if (!structure) {
      return res.status(400).json({ error: '未提供数据结构定义' });
    }
    
    // 初始化OpenAI
    const openaiConfig = {
      apiKey: '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',
    };
    
    const openai = new OpenAI(openaiConfig);
    
    // 构建提示词
    const systemPrompt = `你是一位专业的简历分析师。你需要从用户提供的简历中提取信息，不要编造内容。你需要进行智能推断：
1. 对于技能经验，应该从工作经历中分析，而不是简单地返回0年
2. 对于没有明确提及的日期，给出合理的推断
3. 对于国家/地区代码，需要基于简历中的位置信息给出合理推断
4. 根据工作经历中的时间段，准确计算经验年限
5. 对于所有提取的信息，给出可信度评分(1-10，10表示完全确定)
严格按照用户指定的JSON结构输出。`;

    let userPrompt = `从以下简历中提取信息，进行智能推断和分析。`;
    
    userPrompt += `\n\n简历内容:\n${resumeText}\n\n`;
    userPrompt += `请从中提取以下内容，并进行深度分析：\n`;
    
    // 根据选择的选项添加提取需求，并整合metadata中的预设选项
    const buildFieldPrompt = (fieldName, description, specificInstructions = "") => {
      let promptPart = `- ${description}`;
      if (metadata && metadata[fieldName] && metadata[fieldName].options && metadata[fieldName].options.length > 0) {
        promptPart += ` 对于 ${metadata[fieldName].label || fieldName}, 请主要从以下预设选项中选择：[${metadata[fieldName].options.join(', ')}]。`;
      }
      if (specificInstructions) {
        promptPart += " " + specificInstructions;
      }
      promptPart += "\n";
      return promptPart;
    };

    if (options.includes('languages')) {
      userPrompt += buildFieldPrompt(
        'languages', 
        '语言能力：提取简历中提到的语言及熟练度，评估可信度',
        metadata?.languages?.label ? `熟练度请参考 ${metadata.languages.label} 的预设选项。` : ''
      );
    }
    
    if (options.includes('skills')) {
      userPrompt += buildFieldPrompt(
        'skills', 
        '技能经验：提取简历中的技能，并从工作经历中分析每项技能的实际经验年限，不要返回0年，除非确定是新技能'
      );
    }
    
    if (options.includes('personal_info')) {
      let piInstructions = '提取姓名、电话、电子邮件、地址、国家/地区等个人信息。对于国家代码(country_code)，使用标准的两字母代码(如US、CN)，而不要使用详细格式，系统将自动转换为完整格式。';
      if (metadata?.personal_info?.fields?.country_code?.options) {
        piInstructions += ` 对于国家地区代码, 系统将自动从 ${metadata.personal_info.fields.country_code.label || '国家地区代码'} 的预设选项中匹配完整格式。`;
      }
      userPrompt += buildFieldPrompt('personal_info', `个人资料：${piInstructions}`);
    }
    
    if (options.includes('eeo')) {
       let eeoInstructions = '如性别、种族、退伍军人状态等，只有简历明确提及才提取，否则提供合理推断。对于veteran和disability字段，请使用"yes"或"no"的小写格式。';
       if (metadata?.eeo?.fields) {
           for (const key in metadata.eeo.fields) {
               if (metadata.eeo.fields[key].options && metadata.eeo.fields[key].options.length > 0) {
                   eeoInstructions += ` 对于 ${metadata.eeo.fields[key].label || key}, 请从选项 [${metadata.eeo.fields[key].options.join(', ')}] 中选择。`;
               }
           }
       }
      userPrompt += buildFieldPrompt('eeo', `多样性信息：${eeoInstructions}`);
    }
    
    if (options.includes('salary')) {
      userPrompt += buildFieldPrompt('salary', '期望薪资：如果简历中提到，请提取具体数值和周期（年薪/月薪/时薪）');
    }
    
    if (options.includes('work_experience')) {
      let weInstructions = '提取公司名称、职位、地点、起止时间、职责描述，计算每段工作的持续时间，对于缺失的月份进行合理推断。必须为每项工作经历提供城市信息，如果简历未明确提及，根据公司名称和其他上下文信息推断可能的城市。';
      if (metadata?.work_experience?.fields?.month?.options) {
        weInstructions += ` 对于月份, 请参考 ${metadata.work_experience.fields.month.label || '月份'} 的预设选项（数字格式）。`;
      }
      if (metadata?.work_experience?.fields?.year?.options) {
         //年份选项太多，不直接列出，但AI已知其存在
      }
      userPrompt += buildFieldPrompt('work_experience', `工作经历：${weInstructions}`);
    }
    
    if (options.includes('education')) {
      let eduInstructions = '提取学校、学位、专业、地点、起止时间，对于缺失的月份进行合理推断。每项教育经历必须包含城市信息，如果简历未明确提及，根据学校名称和其他上下文信息推断可能的城市。';
      if (metadata?.education?.fields?.degree?.options) {
        eduInstructions += ` 对于学位, 请参考 ${metadata.education.fields.degree.label || '学位'} 的预设选项。`;
      }
      if (metadata?.education?.fields?.month?.options) {
        eduInstructions += ` 对于月份, 请参考 ${metadata.education.fields.month.label || '月份'} 的预设选项（数字格式）。`;
      }
      userPrompt += buildFieldPrompt('education', `学历经历：${eduInstructions}`);
    }
    
    userPrompt += `\n请严格按照以下JSON结构回复，确保所有内容都符合简历原文，不要编造：\n`;
    userPrompt += JSON.stringify(structure, null, 2);
    userPrompt += `\n\n只包含用户选择的选项，如果简历中找不到相关信息则对应字段使用空数组或空对象。对于所有字段，添加confidence字段(1-10)表示可信度。`;
    userPrompt += `\n\n对于工作和教育经历中的月份，使用数字(1-12)表示，如果简历中没有明确提到月份，给出最合理的推断，并降低confidence值。`;

    // 调用OpenAI API
    const completion = await openai.chat.completions.create({
      model: "gpt-3.5-turbo",
      messages: [
        {role: "system", content: systemPrompt},
        {role: "user", content: userPrompt}
      ],
      temperature: 0.3,
      max_tokens: 2500 
    });

    const content = completion.choices[0].message.content;
    
    // 处理结果
    let aiResult;
    try {
      // 尝试从回复中提取JSON
      const jsonMatch = content.match(/({[\s\S]*})/);
      let jsonContent = jsonMatch ? jsonMatch[0] : content;
      
      // 处理可能的格式问题
      jsonContent = jsonContent.replace(/```json|```/g, '').trim();
      
      // 解析JSON
      aiResult = JSON.parse(jsonContent);
    } catch (jsonError) {
      // 如果无法解析JSON，返回原始内容
      console.error('JSON解析错误:', jsonError);
      console.error('原始AI回复:', content);
      return res.status(500).json({ error: 'JSON解析失败，请查看服务器日志获取原始回复。' });
    }
    
    // 直接返回结果，不再添加服务器端选项
    res.json(aiResult);
  } catch (error) {
    console.error('Error:', error);
    res.status(500).json({ error: error.message || '服务器错误' });
  }
});

app.get('/test', (req, res) => {
  res.json({ status: 'ok', message: 'AI服务器运行正常' });
});

app.listen(port, () => {
  console.log(`AI服务器正在运行，端口: ${port}`);
});