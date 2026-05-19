import boto3

client = boto3.client(
    'rekognition',
    aws_access_key_id='AKIAWWJIEP3GN5ZFX3RS',
    aws_secret_access_key='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',
    region_name='ap-south-1'
)

with open('images/test.jpg', 'rb') as image:
    response = client.detect_faces(
        Image={'Bytes': image.read()},
        Attributes=['ALL']
    )

print(response)