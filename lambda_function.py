import json
import urllib.parse
import boto3
from datetime import datetime

# Initialize AWS SDK clients (Boto3)
s3_client = boto3.client('s3')
sns_client = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')

# Configuration
DEST_BUCKET = "processed-photos-bram"  
SNS_TOPIC_ARN = "arn:aws:sns:ap-south-1:REDACTED_ACCOUNT_ID:ImageProcessingAlerts" # Keep your ID safe!

# Connect to our DynamoDB table
table = dynamodb.Table('UploadedPhotos')

def lambda_handler(event, context):
    try:
        # 1. Find out which file was uploaded to your source S3 bucket
        source_bucket = event['Records'][0]['s3']['bucket']['name']
        image_key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
        
        print(f"New image detected: {image_key} in bucket: {source_bucket}")
        
        # 2. Copy the file directly to your backup/destination bucket
        copy_source = {'Bucket': source_bucket, 'Key': image_key}
        destination_key = f"processed-{image_key}"
        
        s3_client.copy_object(
            CopySource=copy_source, 
            Bucket=DEST_BUCKET, 
            Key=destination_key
        )
        print(f"Successfully copied file to {DEST_BUCKET}")
        
        # 3. Save metadata log to DynamoDB
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        table.put_item(
            Item={
                'PhotoID': image_key,            # Unique Partition Key
                'UploadTime': timestamp,         # Date and time
                'SourceBucket': source_bucket,   # Where it came from
                'BackupKey': destination_key     # The new file name
            }
        )
        print(f"Successfully saved {image_key} metadata to DynamoDB")
        
        # 4. Send an email notification via SNS
        message_text = f"Success! Your photo '{image_key}' has been processed, backed up to S3, and logged in DynamoDB."
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=message_text,
            Subject="📷 New Photo Processed & Logged!"
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps('File completely processed!')
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise e
