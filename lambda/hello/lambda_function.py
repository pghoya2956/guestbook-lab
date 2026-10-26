# 오늘의 한마디 (1학년 16단원). 앱의 HELLO_API_URL 에 이 함수의 API 주소를 넣으면 앱이 여기서 받아 간다.
import json
import random

MSGS = ["오늘도 화이팅", "커밋은 자주", "정리는 실력"]


def lambda_handler(event, context):
    body = {"message": random.choice(MSGS)}
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": json.dumps(body, ensure_ascii=False),
    }
