var _ = require('lodash')
var md5 = require('blueimp-md5')
var {Pool, Client} = require('pg')
var {parseAnswerV1_0ToV2_2, parseAnswerV2_0ToV2_2} = require('./util/upgrade-answer.cjs')

async function upgradeAnswer(data) {
  if (!data) {
    console.log('answer data is null, pass')
    return null
  }

  if (!data.userAnswer) {
    console.log('answer is empty, pass')
    return null
  }

  if (data.userAnswer.version == '2.2') {
    console.log('answer version is 2.2, pass')
    return null
  }

  const newAnswer = {
    'userAnswer': null,
    'schema': data.schema
  }

  if (!data.userAnswer.items) {
    newAnswer['userAnswer'] = parseAnswerV1_0ToV2_2(data.userAnswer, data.schema)
  } else {
    newAnswer['userAnswer'] = {
      items: parseAnswerV2_0ToV2_2(data.userAnswer.items),
      version: '2.2',
    }
  }

  return newAnswer
}

async function doUpgradeAnswer(client, row) {
  console.log(row.id, row.qid)
  const newAnswer = await upgradeAnswer(row.data)
  if (newAnswer == null) {
    return
  }

  console.log('updating answer ', row.id, row.qid)
  await client.query('update answer set data=$1 where id=$2', [newAnswer, row.id])
}

async function doUpgradeQuestion(client, row) {
  console.log(row.id)
  const newAnswer = await upgradeAnswer(row.preset_answer)
  if (newAnswer == null) {
    return
  }

  console.log('updating question ', row.id)
  await client.query('update question set preset_answer=$1 where id=$2', [newAnswer, row.id])
}

(async () => {
  // "postgresql://postgres@127.0.0.1:35355/draft"
  console.log(process.argv)
  const pool = new Pool({connectionString: process.argv[process.argv.length-1]})
  const client = await pool.connect()

  const BATCH_SIZE = 100

  const answerCountResult = await client.query('select count(1) from answer;')
  const answerCount = answerCountResult['rows'][0]['count']
  for (let i = 0; i < answerCount / BATCH_SIZE; i++) {
    const {rows: answerRows} = await client.query('select id, qid, data from answer order by id offset $1 limit $2;', [i * BATCH_SIZE, BATCH_SIZE])
    for(var row of answerRows) {
      try {
        await client.query('BEGIN')
        await doUpgradeAnswer(client, row)
        await client.query('COMMIT')
      } catch(e) {
        await client.query('ROLLBACK')
        console.log('ERROR: ', row)
        console.log('stacktrace: ', e.stack)
      }
    }
  }

  const questionCountResult = await client.query('select count(1) from question;')
  const questionCount = questionCountResult['rows'][0]['count']
  for (let i = 0; i < questionCount / BATCH_SIZE; i++) {
    const {rows: questionRows} = await client.query('select id, preset_answer from question where preset_answer is not null order by id offset $1 limit $2;', [i * BATCH_SIZE, BATCH_SIZE])
    for(var row of questionRows) {
      try {
        await client.query('BEGIN')
        await doUpgradeQuestion(client, row)
        await client.query('COMMIT')
      } catch(e) {
        await client.query('ROLLBACK')
        console.log('ERROR: ', row)
        console.log('stacktrace: ', e.stack)
      }
    }
  }


  client.release()

})().catch(e => console.error(e.stack))

// var test_old = {"461f84920ba33beca20b53f98f114e04": {"type": "Wml", "label": "Wml", "schemaPath": ["Wml"], "md5": "461f84920ba33beca20b53f98f114e04", "attributes": [], "items": []}, "57ffc1ea66bc4c7f7bdd3c5ceac95fc1": {"label": "test2", "type": "\u6587\u672c", "multiple": false, "required": true, "words": "", "attributes": [{"multiple": false, "name": "test2", "required": true, "type": "\u6587\u672c"}], "items": [{"fields": [{"components": [{"frameData": {"height": "23.017183999999986", "id": "page2:1543930402400", "left": "123.02288000000001", "page": 1, "top": "353.1947200000001", "topleft": ["353.1947200000001", "123.02288000000001"], "type": "test2", "width": "376.2119040000001"}, "text": "\u4f46\u7fa9\u4eba\u7684\u8def\u597d\u50cf\u9ece\u660e\u7684\u5149\uff0c\u8d8a\u7167\u8d8a\u660e\uff0c\u76f4\u5230\u65e5\u5348\u3002"}], "name": "test2", "label": "\u4f46\u7fa9\u4eba\u7684\u8def\u597d\u50cf\u9ece\u660e\u7684\u5149\uff0c\u8d8a\u7167\u8d8a\u660e\uff0c\u76f4\u5230\u65e5\u5348\u3002"}], "schemaMD5": "57ffc1ea66bc4c7f7bdd3c5ceac95fc1", "enumLabel": ""}, {"fields": [{"components": [{"frameData": {"height": "23.810879999999997", "id": "page2:1543930402400", "left": "421.4525760000001", "page": 1, "top": "399.22908800000005", "topleft": ["399.22908800000005", "421.4525760000001"], "type": "test2", "width": "92.068736"}, "text": "\u7bb4\u8a004:18"}], "name": "test2", "label": "\u7bb4\u8a004:18"}], "schemaMD5": "57ffc1ea66bc4c7f7bdd3c5ceac95fc1", "enumLabel": ""}], "md5": "57ffc1ea66bc4c7f7bdd3c5ceac95fc1", "schemaPath": ["Wml", "test2"]}, "f2a0ac30dd5ee4c6ef0df23ef0769cdc": {"type": "\u65e5\u671f", "label": "test3", "schemaPath": ["Wml", "test3"], "md5": "f2a0ac30dd5ee4c6ef0df23ef0769cdc", "required": false, "multiple": true, "attributes": [{"name": "test3", "multiple": true, "required": false, "type": "\u65e5\u671f"}], "items": []}, "b7540eb2536dd3d03e037a69ad6b00c1": {"type": "\u6570\u5b57", "label": "test4", "schemaPath": ["Wml", "test4"], "md5": "b7540eb2536dd3d03e037a69ad6b00c1", "required": false, "multiple": true, "attributes": [{"name": "test4", "multiple": true, "required": false, "type": "\u6570\u5b57"}], "items": []}, "2b0e9f86aeee3cf015c9b186c1805bb2": {"type": "\u679a\u4e3e1", "label": "test5", "schemaPath": ["Wml", "test5"], "md5": "2b0e9f86aeee3cf015c9b186c1805bb2", "required": false, "multiple": true, "attributes": [{"name": "test5", "multiple": true, "required": false, "type": "\u679a\u4e3e1"}], "items": []}, "cfee2298f98073eb6cb51f5d34b35ca8": {"type": "\u679a\u4e3e2", "label": "test6", "schemaPath": ["Wml", "test6"], "md5": "cfee2298f98073eb6cb51f5d34b35ca8", "required": false, "multiple": true, "attributes": [{"name": "test6", "multiple": true, "required": false, "type": "\u679a\u4e3e2"}], "items": []}, "421232093da03a185e76dfc49deef83d": {"type": "\u5185\u5bb9", "label": "\u5185\u5bb9", "schemaPath": ["Wml", "\u5185\u5bb9"], "md5": "421232093da03a185e76dfc49deef83d", "required": false, "multiple": true, "attributes": [{"name": "\u7b2c\u4e00\u6bb5", "multiple": true, "required": false, "type": "\u6587\u672c"}, {"name": "\u7b2c\u4e8c\u6bb5", "multiple": true, "required": false, "type": "\u6587\u672c"}, {"name": "\u7b2c\u4e09\u6bb5", "multiple": true, "required": false, "type": "\u6587\u672c"}, {"name": "\u7b2c\u56db\u6bb5", "multiple": true, "required": false, "type": "\u6587\u672c"}], "items": [{"fields": [{"components": [], "label": "", "name": "\u7b2c\u4e00\u6bb5", "type": "\u6587\u672c"}, {"components": [], "label": "", "name": "\u7b2c\u4e8c\u6bb5", "type": "\u6587\u672c"}, {"components": [], "label": "", "name": "\u7b2c\u4e09\u6bb5", "type": "\u6587\u672c"}, {"components": [], "label": "", "name": "\u7b2c\u56db\u6bb5", "type": "\u6587\u672c"}], "schemaMD5": "421232093da03a185e76dfc49deef83d"}]}, "d08898fcd313fdab5ed44ddc34131f08": {"type": "test7", "label": "test7", "schemaPath": ["Wml", "test7"], "md5": "d08898fcd313fdab5ed44ddc34131f08", "required": false, "multiple": true, "attributes": [{"name": "A1", "multiple": true, "required": false, "type": "\u6587\u672c"}, {"name": "A2", "multiple": true, "required": false, "type": "\u679a\u4e3e1"}, {"name": "A3", "multiple": false, "required": false, "type": "\u679a\u4e3e2"}], "items": [{"fields": [{"components": [], "label": "", "name": "A1", "type": "\u6587\u672c"}, {"components": [], "label": "", "name": "A2", "type": "\u679a\u4e3e1"}, {"components": [], "label": "", "name": "A3", "type": "\u679a\u4e3e2"}], "schemaMD5": "d08898fcd313fdab5ed44ddc34131f08"}]}, "f75c676d49caad772ba778d9adce047d": {"type": "test8", "label": "test8", "schemaPath": ["Wml", "test8"], "md5": "f75c676d49caad772ba778d9adce047d", "required": false, "multiple": true, "attributes": [{"name": "A4", "multiple": false, "required": false, "type": "\u6587\u672c"}, {"name": "A5", "multiple": false, "required": true, "type": "\u679a\u4e3e2"}, {"name": "A6", "multiple": true, "required": false, "type": "\u679a\u4e3e2"}, {"name": "A7", "multiple": true, "required": false, "type": "\u679a\u4e3e1"}], "items": [{"fields": [{"components": [], "label": "", "name": "A4", "type": "\u6587\u672c"}, {"components": [], "label": "", "name": "A5", "type": "\u679a\u4e3e2"}, {"components": [], "label": "", "name": "A6", "type": "\u679a\u4e3e2"}, {"components": [], "label": "", "name": "A7", "type": "\u679a\u4e3e1"}], "schemaMD5": "f75c676d49caad772ba778d9adce047d"}]}, "95db39e8e68373dac185bd490d4ed14f": {"type": "test9", "label": "test9", "schemaPath": ["Wml", "test9"], "md5": "95db39e8e68373dac185bd490d4ed14f", "required": true, "multiple": false, "attributes": [{"name": "A8", "multiple": true, "required": false, "type": "\u679a\u4e3e1"}, {"name": "A9", "multiple": true, "required": false, "type": "\u679a\u4e3e2"}, {"name": "A10", "multiple": true, "required": false, "type": "\u679a\u4e3e2"}, {"name": "A11", "multiple": true, "required": false, "type": "\u6587\u672c"}, {"name": "test12", "multiple": false, "required": true, "type": "\u6570\u5b57"}], "items": [{"fields": [{"components": [], "label": "", "name": "A8", "type": "\u679a\u4e3e1"}, {"components": [], "label": "", "name": "A9", "type": "\u679a\u4e3e2"}, {"components": [], "label": "", "name": "A10", "type": "\u679a\u4e3e2"}, {"components": [], "label": "", "name": "A11", "type": "\u6587\u672c"}, {"components": [], "label": "", "name": "test12", "type": "\u6570\u5b57"}], "schemaMD5": "95db39e8e68373dac185bd490d4ed14f"}]}, "fd561c5945f8cd90606b0dec3be2cd7a": {"label": "\u65e5\u671f", "type": "\u65e5\u671f", "multiple": true, "required": true, "words": "", "attributes": [{"multiple": true, "name": "\u65e5\u671f", "required": true, "type": "\u65e5\u671f"}], "items": [{"fields": [{"components": [{"frameData": {"height": "17.96079310344828", "id": "page2:1543930402401", "left": "416.9469827586207", "page": 1, "top": "357.9329482758621", "topleft": ["357.9329482758621", "416.9469827586207"], "type": "\u65e5\u671f", "width": "62.22131896551724"}, "text": "\u76f4\u5230\u65e5\u5348"}], "name": "\u65e5\u671f", "label": "\u76f4\u5230\u65e5\u5348"}], "schemaMD5": "fd561c5945f8cd90606b0dec3be2cd7a", "enumLabel": ""}], "md5": "fd561c5945f8cd90606b0dec3be2cd7a", "schemaPath": ["Wml", "\u65e5\u671f"]}, "60f52d46f4b355a7c0477c4c066a7686": {"type": "\u6570\u5b57", "label": "\u6570\u5b57\u6539\u6539", "schemaPath": ["Wml", "\u6570\u5b57\u6539\u6539"], "md5": "60f52d46f4b355a7c0477c4c066a7686", "required": true, "multiple": true, "attributes": [{"name": "\u6570\u5b57\u6539\u6539", "multiple": true, "required": true, "type": "\u6570\u5b57"}], "items": []}, "6ccfa5e71663d85b867a98ab407077a9": {"type": "\u6587\u672c", "label": "\u5e94\u6536\u7968\u636eedit", "schemaPath": ["Wml", "\u5e94\u6536\u7968\u636eedit"], "md5": "6ccfa5e71663d85b867a98ab407077a9", "required": false, "multiple": true, "attributes": [{"name": "\u5e94\u6536\u7968\u636eedit", "multiple": true, "required": false, "type": "\u6587\u672c"}], "items": []}}

// var test_schema = {"schemas": [{"name": "Wml", "orders": ["test2", "test3", "test4", "test5", "test6", "\u5185\u5bb9", "test7", "test8", "test9", "\u65e5\u671f", "\u6570\u5b57\u6539\u6539", "\u5e94\u6536\u7968\u636eedit"], "schema": {"test2": {"type": "\u6587\u672c", "required": true, "multi": false, "name": "test2", "_index": 43}, "test3": {"type": "\u65e5\u671f", "required": false, "multi": true, "name": "test3", "_index": 44}, "test4": {"type": "\u6570\u5b57", "required": false, "multi": true, "name": "test4", "_index": 45}, "test5": {"type": "\u679a\u4e3e1", "required": false, "multi": true, "name": "test5", "_index": 46}, "test6": {"type": "\u679a\u4e3e2", "required": false, "multi": true, "name": "test6", "_index": 47}, "\u5185\u5bb9": {"type": "\u5185\u5bb9", "required": false, "multi": true, "name": "\u5185\u5bb9", "_index": 48}, "test7": {"type": "test7", "required": false, "multi": true, "name": "test7", "_index": 49}, "test8": {"type": "test8", "required": false, "multi": true, "name": "test8", "_index": 50}, "test9": {"type": "test9", "required": true, "multi": false, "name": "test9", "_index": 51}, "\u65e5\u671f": {"type": "\u65e5\u671f", "required": true, "multi": true, "name": "\u65e5\u671f", "_index": 52}, "\u6570\u5b57\u6539\u6539": {"type": "\u6570\u5b57", "required": true, "multi": true, "name": "\u6570\u5b57\u6539\u6539", "_index": 53}, "\u5e94\u6536\u7968\u636eedit": {"type": "\u6587\u672c", "required": false, "multi": true, "name": "\u5e94\u6536\u7968\u636eedit", "_index": 54}}}, {"name": "\u5185\u5bb9", "orders": ["\u7b2c\u4e00\u6bb5", "\u7b2c\u4e8c\u6bb5", "\u7b2c\u4e09\u6bb5", "\u7b2c\u56db\u6bb5"], "schema": {"\u7b2c\u4e00\u6bb5": {"type": "\u6587\u672c", "required": false, "multi": true, "name": "\u7b2c\u4e00\u6bb5", "_index": 56}, "\u7b2c\u4e8c\u6bb5": {"type": "\u6587\u672c", "required": false, "multi": true, "name": "\u7b2c\u4e8c\u6bb5", "_index": 57}, "\u7b2c\u4e09\u6bb5": {"type": "\u6587\u672c", "required": false, "multi": true, "name": "\u7b2c\u4e09\u6bb5", "_index": 58}, "\u7b2c\u56db\u6bb5": {"type": "\u6587\u672c", "required": false, "multi": true, "name": "\u7b2c\u56db\u6bb5", "_index": 59}}}, {"name": "\u91cd\u8981\u5185\u5bb9", "orders": ["\u7b2c\u4e00\u90e8\u5206", "\u7b2c\u4e8c\u90e8\u5206"], "schema": {"\u7b2c\u4e00\u90e8\u5206": {"type": "\u6587\u672c", "required": false, "multi": true, "name": "\u7b2c\u4e00\u90e8\u5206", "_index": 61}, "\u7b2c\u4e8c\u90e8\u5206": {"type": "\u679a\u4e3e1", "required": false, "multi": true, "name": "\u7b2c\u4e8c\u90e8\u5206", "_index": 62}}}, {"name": "\u603b\u7ed3", "orders": ["\u603b\u7ed3\u90e8\u5206"], "schema": {"\u603b\u7ed3\u90e8\u5206": {"type": "\u6587\u672c", "required": false, "multi": true, "name": "\u603b\u7ed3\u90e8\u5206", "_index": 64}}}, {"name": "test7", "orders": ["A1", "A2", "A3"], "schema": {"A1": {"type": "\u6587\u672c", "required": false, "multi": true, "name": "A1", "_index": 66}, "A2": {"type": "\u679a\u4e3e1", "required": false, "multi": true, "words": "\u4e8c\u7ea7\u679a\u4e3e\u5b57\u6bb5\u63cf\u8ff0", "name": "A2", "_index": 67}, "A3": {"type": "\u679a\u4e3e2", "required": false, "multi": false, "name": "A3", "_index": 68}}}, {"name": "test8", "orders": ["A4", "A5", "A6", "A7"], "schema": {"A4": {"type": "\u6587\u672c", "required": false, "multi": false, "name": "A4", "_index": 70}, "A5": {"type": "\u679a\u4e3e2", "required": true, "multi": false, "name": "A5", "_index": 71}, "A6": {"type": "\u679a\u4e3e2", "required": false, "multi": true, "name": "A6", "_index": 72}, "A7": {"type": "\u679a\u4e3e1", "required": false, "multi": true, "name": "A7", "_index": 73}}}, {"name": "test9", "orders": ["A8", "A9", "A10", "A11", "test12"], "schema": {"A8": {"type": "\u679a\u4e3e1", "required": false, "multi": true, "name": "A8", "_index": 75}, "A9": {"type": "\u679a\u4e3e2", "required": false, "multi": true, "name": "A9", "_index": 76}, "A10": {"type": "\u679a\u4e3e2", "required": false, "multi": true, "words": "\u6700\u540e\u4e00\u4e2a\u4e8c\u7ea7\u679a\u4e3e\u5b57\u6bb5\u63cf\u8ff0", "name": "A10", "_index": 77}, "A11": {"type": "\u6587\u672c", "required": false, "multi": true, "name": "A11", "_index": 78}, "test12": {"type": "\u6570\u5b57", "required": true, "multi": false, "name": "test12", "_index": 79}}}, {"name": "text", "orders": [], "schema": {}}], "schema_types": [{"label": "\u679a\u4e3e1", "values": [{"name": "1", "isDefault": false}, {"name": "2", "isDefault": false}, {"name": "3", "isDefault": false}], "type": "enum"}, {"label": "\u679a\u4e3e2", "values": [{"name": "4", "isDefault": false}, {"name": "5", "isDefault": true}, {"name": "6", "isDefault": false}], "type": "enum"}], "version": "6218478e503a8872627f1e78643bba89"}

// var x = parseAnswerV1_0ToV2_2(test_old, test_schema)
// console.log(x)
