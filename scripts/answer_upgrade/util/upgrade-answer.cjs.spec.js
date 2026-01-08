const expect = require('chai').expect;
const { schema, answerV1, answerV2_2 } = require('./upgrade-answer.cjs.mock');
const {
  parseAnswerV1_0ToV2_2,
  parseAnswerV2_0ToV2_2,
} = require('./upgrade-answer.cjs');
// import { parseAnswerToV2_2 } from '../../src/utils/answer-translateV2.2';

describe('测试演示', function() {
  it('1 + 1 should be eq 2', function() {
    expect(1 + 1).to.be.equal(2);
  });
});

const answer2_0 = [
  { key: '["LRs","A1"]', data: [], schema: {} },
  { key: '["LRs","A2"]', data: [], schema: {} },
  { key: '["LRs","A3"]', data: [], schema: {} },
  { key: '["LRs","A10"]', data: [], schema: {} },
  { key: '["LRs","A10","Country road:0"]', data: [], schema: {} },
  { key: '["LRs:0","A10:0","Country of operation:0"]', data: [], schema: {} },
];
describe('答案升级', function() {
  it('v1.0 -> v2.0', function() {
    let newAnswer = parseAnswerV1_0ToV2_2(answerV1, schema);
    expect(newAnswer).to.be.deep.eq(answerV2_2);
  });
  it('v2.0 -> v2.2', function() {
    let answer2_2 = parseAnswerV2_0ToV2_2(answer2_0);
    expect(answer2_2.map(answer => answer.key)).to.be.deep.eq([
      '["LRs:0","A1:0"]',
      '["LRs:0","A2:0"]',
      '["LRs:0","A3:0"]',
      '["LRs:0","A10:0"]',
      '["LRs:0","A10:0","Country road:0:0"]',
      '["LRs:0","A10:0","Country of operation:0"]',
    ]);
  });
});
