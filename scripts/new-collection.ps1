param(
    [Parameter(Mandatory=$true)]
    [String]$collectionid,

    [Parameter(Mandatory=$true)]
    [String]$region
)

aws rekognition create-collection --collection-id $collectionid --region $region
aws rekognition list-collections