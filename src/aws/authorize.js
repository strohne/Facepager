var AWS = require('aws-sdk');
var s3 = new AWS.S3();
var bucketName = 'facepager-users';

// Authorize by module and usertoken parameters

exports.handler = async (event) => {
  
      // Default response
      let response = {
          statusCode: 401,
          body: JSON.stringify('Not authorized.'),
      };    


      try {
        
        // Get bucketKey
        let bucketKey = getBucketKey(event);

        // Get item for user
        let data = await getBucketItem(bucketKey);
        console.log(data)
        
        // Check blacklist...
        if (data.status != 'allowed')
          throw "Not authorized!"
                
        // Add to whitelist...
        await createBucketItem(bucketKey,'allowed')
        
        response = {
            statusCode: 200,
            body: JSON.stringify('Successfully authorized!'),
        };
    } catch(e) {
      console.log(e)
    }
    
    return response;
};


// Get bucket key from module and usertoken
function getBucketKey(event){
    let usertoken = '';
    let module = '';
    if (event.queryStringParameters && event.queryStringParameters.usertoken) {
        usertoken = event.queryStringParameters.usertoken.replace(/[\W_]+/g,"");
    } 
    if (event.queryStringParameters && event.queryStringParameters.module) {
        module = event.queryStringParameters.module.replace(/[\W_]+/g,"");
    } 

    if ((module == '') || (usertoken == '')) 
      throw "Missing authorization data."
    
    return module+'/'+usertoken;
}


// Get bucket item
async function getBucketItem(bucketKey) {
  try {
    let bucketParams = {Bucket: bucketName, Key: bucketKey};
    let item = await s3.getObject(bucketParams).promise();
    return JSON.parse(item.Body.toString('utf-8'))
  } catch (e) {
    return {};
  }
}

// Create bucket item
async function createBucketItem(bucketKey,status){
  let bucketContent = {'timestamp':Date.now(),'token':bucketKey,'status':status};
  let bucketParams = {Bucket: bucketName, Key: bucketKey, Body: JSON.stringify(bucketContent)};
  
  return s3.putObject(bucketParams).promise();
}