import os
from flask import Flask, Response, request
from twilio.twiml.voice_response import VoiceResponse
from openai import OpenAI
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# OpenAIクライアントの初期化
# 環境変数からAPIキーを読み込むのが安全です
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

app = Flask(__name__)

# 会話履歴を保存するための簡単なリスト
conversation_history = []

@app.route("/voice", methods=['GET', 'POST'])
def voice():
    """電話がかかってきたときに最初に応答する関数"""
    
    # 新しい電話がかかってきたら、会話履歴をリセット
    conversation_history.clear()

    # AIに最初の役割を与えるシステムプロンプト
    system_prompt = {
        "role": "system", 
        "content": """
        あなたは「さくら」という名前の、親切で少しユーモアのあるAIアシスタントです。
        ユーザーからのどんな質問にも、自然な会話で応答してください。
        専門的すぎる質問や答えられない質問には、「うーん、それは私の専門外みたいです。他の質問はありますか？」のように、正直に答えてください。
        常に簡潔で、人間らしい応答を心がけてください。
        """
    }
    conversation_history.append(system_prompt)

    response = VoiceResponse()
    gather = response.gather(input='speech', language='ja-JP', timeout=4, action='/handle-ai-speech', method='POST')
    gather.say('こんにちは、AIアシスタントのさくらです。ご用件をどうぞ。', language='ja-JP')
    
    # タイムアウトした場合の応答
    response.say('応答がありませんでした。お電話ありがとうございました。', language='ja-JP')
    
    return Response(str(response), mimetype='text/xml')


@app.route("/handle-ai-speech", methods=['GET', 'POST'])
def handle_ai_speech():
    """ユーザーの発話を受け取り、AIの応答を生成する関数"""
    
    # ユーザーが話した内容をテキストで取得
    speech_text = request.form.get('SpeechResult')
    
    response = VoiceResponse()

    # ユーザーが何か話した場合のみAIを呼び出す
    if speech_text:
        try:
            # ユーザーの発話を会話履歴に追加
            conversation_history.append({"role": "user", "content": speech_text})

            # OpenAIのAPIを呼び出す (会話履歴全体を渡す)
            chat_completion = client.chat.completions.create(
                model="gpt-4o",
                messages=conversation_history
            )
            
            # AIが生成した応答テキストを取得
            ai_response_text = chat_completion.choices[0].message.content
            
            # AIの応答も会話履歴に追加
            conversation_history.append({"role": "assistant", "content": ai_response_text})

            # AIの応答をユーザーに話し、続けてユーザーの入力を待つ
            gather = response.gather(input='speech', language='ja-JP', timeout=4, action='/handle-ai-speech', method='POST')
            gather.say(ai_response_text, language='ja-JP')

            # もしユーザーが何も話さずに会話を終えた場合の最後の挨拶
            response.say('また何かあればお電話くださいね。', language='ja-JP')

        except Exception as e:
            print(f"An error occurred: {e}")
            response.say('申し訳ありません。システムにエラーが発生しました。お手数ですが、もう一度おかけ直しください。', language='ja-JP')

    else:
        # うまく聞き取れなかった場合
        response.say('すみません、うまく聞き取れませんでした。もう一度お話しいただけますか？', language='ja-JP')
        # もう一度、同じ会話のターンで入力を促す
        response.redirect('/handle-ai-speech-reprompt')

    return Response(str(response), mimetype='text/xml')

@app.route("/handle-ai-speech-reprompt", methods=['GET', 'POST'])
def handle_ai_speech_reprompt():
    """聞き取れなかった場合に、再度入力を促すための関数"""
    response = VoiceResponse()
    gather = response.gather(input='speech', language='ja-JP', timeout=4, action='/handle-ai-speech', method='POST')
    # AIの最後の発言を繰り返すことも可能ですが、ここではシンプルに
    # gather.say('もう一度お願いします。', language='ja-JP')
    
    # もしユーザーが何も話さずに会話を終えた場合の最後の挨拶
    response.say('また何かあればお電話くださいね。', language='ja-JP')
    return Response(str(response), mimetype='text/xml')


if __name__ == "__main__":
    app.run(debug=True)