import requests

text = "Hi from Mercury" 

def send_message(text):
    bot_token = '6401018800:AAGJBMX_YkhZu-4XJEw19Of2HevZXBqo7z4'
    chat_id = -1001905455526
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode":"Markdown"
    }
    
    response = requests.post(url, data=data)
    # if response.status_code == 200:
    #     print("Message sent successfully!")
    # else:
    #     print("Error sending message:", response.text)
