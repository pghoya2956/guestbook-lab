# 서버리스 리뷰 API (2학년 11단원). API Gateway HTTP API(페이로드 2.0) + DynamoDB 테이블 guestbook.
import json
import os
import time
import uuid

import boto3

table = boto3.resource("dynamodb").Table(os.environ.get("TABLE", "guestbook"))


def lambda_handler(event, context):
    if event["requestContext"]["http"]["method"] == "POST":
        b = json.loads(event.get("body") or "{}")
        item = {
            "id": str(uuid.uuid4()),
            "ts": int(time.time()),
            "name": b.get("name", "익명"),
            "msg": b.get("msg", ""),
        }
        table.put_item(Item=item)
        return {"statusCode": 201}
    # 같은 테이블에 앱이 남긴 지난 날 메뉴(id 가 menu# 로 시작)는 리뷰가 아니라 뺀다
    items = [i for i in table.scan(Limit=50)["Items"] if not str(i.get("id", "")).startswith("menu#")]
    # DynamoDB 는 숫자를 Decimal 로 돌려준다. default=str 이 없으면 json.dumps 가 실패한다
    return {"statusCode": 200, "body": json.dumps(items, ensure_ascii=False, default=str)}
