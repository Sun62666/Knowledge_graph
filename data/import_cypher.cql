// 企业知识图谱CQL导入脚本
// 自动生成，请勿手动修改

MERGE (a:Entity {name: '华为技术有限公司'}) MERGE (b:Entity {name: '深圳'}) MERGE (a)-[:`位于`]->(b);
MERGE (a:Entity {name: '马云'}) MERGE (b:Entity {name: '阿里巴巴集团'}) MERGE (a)-[:`创建`]->(b);
MERGE (a:Entity {name: '华为'}) MERGE (b:Entity {name: '5G通信设备'}) MERGE (a)-[:`研发`]->(b);
MERGE (a:Entity {name: '腾讯'}) MERGE (b:Entity {name: '字节跳动'}) MERGE (a)-[:`投资`]->(b);
MERGE (a:Entity {name: '张三'}) MERGE (b:Entity {name: '阿里巴巴的技术总监'}) MERGE (a)-[:`任职`]->(b);
MERGE (a:Entity {name: '张三'}) MERGE (b:Entity {name: '技术总监'}) MERGE (a)-[:`任职`]->(b);
MERGE (a:Entity {name: '百度'}) MERGE (b:Entity {name: '2000年'}) MERGE (a)-[:`成立`]->(b);
MERGE (a:Entity {name: '李彦宏'}) MERGE (b:Entity {name: '百度'}) MERGE (a)-[:`创建`]->(b);