HTTP 响应状态码，只有成功响应才是 200，其他情况下我们会使用 HTTP 状态码来当成业务状态码，这 样前端通过 业务状态码 来判断操作是否成功，减少前端的判断。发生错误时，需要在 message 和
data 中携带相应的错误与描述信息。

{
"code": 200, // 响应状态
"message": "获取AI应用数据成功", // 业务消息提示 "data": {} // 业务获取的数据
}

HTTP 响应状态码如下:
200:成功响应，表示请求处理成功;
400:Bad Request，表示客户端请求发生错误;
404:Not Found Error，表示请求资源不存在;
422:Validatiton Error，表示请求数据校验发生错误;
429:Too Many Requests Error，表示请求过多并发限制错误;
500:Server Error，服务器发生错误;

另外如果数据为列表型分页数据，则在 data 中存在两个字段 paginator 和 list ，分别代表分页的数 据信息，响应的数据列表信息，数据格式如下所示:

{
"code": 200,
"message": "",
"data": {
"paginator": {
"page_size": 10, // 当前页数每页条数
"current_page": 1,// 当前页数
"total_page": 10, // 总页数
"total_record": 100 // 总记录条数
},
"list": [], // 分页的列表数据 }
}