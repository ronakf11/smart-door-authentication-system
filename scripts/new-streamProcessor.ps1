param(
    [Parameter(Mandatory=$true)]
    [String]$region,

    [String]$cliInputJson = 'file://kinesisSmartDoor.json',
    [String]$name = ((Get-content (($cliInputJson -split '//')[1]) | Select-String name) -split '"')[3]
)

aws rekognition create-stream-processor --region $region --cli-input-json $cliInputJson
aws rekognition list-stream-processors
aws rekognition describe-stream-processor --name $name
aws rekognition start-stream-processor --name $name
aws rekognition list-stream-processors