// Global
const glob = {
  CHANGE_MENUACTIVE: 'CHANGE_MENUACTIVE',
  CHANGE_MENU_VISIBLE: 'CHANGE_MENU_VISIBLE',
  SET_USER: 'SET_USER',
  jumpToMenuItem: 'jumpToMenuItem',
  fetchProjectItems: 'fetchProjectItems',
  fetchTags: 'fetchTags',
  fetchPDFDocument: 'fetchPDFDocument',
  login: 'login',
  logout: 'logout',
  getUserLocalInfo: 'getUserLocalInfo',
};

// Modules
const project = {
  module: 'projectModule',
  SET_PROJECTS: 'SET_PROJECTS',
  SET_CUR_PROJECT: 'SET_CUR_PROJECT',
  SET_EMPTY_PROJECT: 'SET_EMPTY_PROJECT',
  SET_LOADING: 'SET_LOADING',
  fetchProjects: 'fetchProjects',
  persistProject: 'persistProject',
  deleteProject: 'deleteProject',
};

const summary = {
  module: 'summaryModule',
  SET_SUMMARY: 'SET_SUMMARY',
  SET_LOADING: 'SET_LOADING',
  fetchSummary: 'fetchSummary',
};

const user = {
  module: 'userModule',
  SET_LOADING: 'SET_LOADING',
  SET_USERS: 'SET_USERS',
  SET_CUR_USER: 'SET_CUR_USER',
  SET_EMPTY_USER: 'SET_EMPTY_USER',
  fetchUsers: 'fetchUsers',
  persistUser: 'persistUser',
  deleteUser: 'deleteUser',
};

const tag = {
  module: 'tagModule',
  SET_TAGS: 'SET_TAGS',
  SET_CUR_TAG: 'SET_CUR_TAG',
  SET_EMPTY_TAG: 'SET_EMPTY_TAG',
  fetchTags: 'fetchTags',
  persistTag: 'persistTag',
  deleteTag: 'deleteTag',
};

const detail = {
  module: 'detailModule',
  SET_FILES: 'SET_FILES',
  SET_DIR_ID: 'SET_DIR_ID',
  SET_LOADING: 'SET_LOADING',
  SET_FILEPATH: 'SET_FILEPATH',
  SET_CUR_FILE: 'SET_CUR_FILE',
  fetchFileList: 'fetchFileList',
  createFolder: 'createFolder',
  fetchBoxText: 'fetchBoxText',
  sendQuestionAnswer: 'sendQuestionAnswer',
  uploadFile: 'uploadFile',
  deleteFile: 'deleteFile',
  lockFile: 'lockFile',
};

const file = {
  module: 'fileModule',
  SET_ALL_FILES: 'SET_ALL_FILES',
  SET_ANSWERED_FILES: 'SET_ANSWERED_FILES',
  SET_TAGGED_FILES: 'SET_TAGGED_FILES',
  SET_CONFLICT_FILES: 'SET_CONFLICT_FILES',
  SET_ALL_LOADING: 'SET_ALL_LOADING',
  SET_ANSWERED_LOADING: 'SET_ANSWERED_LOADING',
  fetchAllFiles: 'fetchAllFiles',
  fetchAnsweredFiles: 'fetchAnsweredFiles',
  fetchTaggedFiles: 'fetchTaggedFiles',
  fetchConflictFiles: 'fetchConflictFiles',
};

const dashboard = {
  module: 'dashboardModule',
  SET_REVIEW_SUMMARY: 'SET_REVIEW_SUMMARY',
  SET_MODEL_ACCURACY_SCORE: 'SET_MODEL_ACCURACY_SCORE',
  SET_LOADING: 'SET_LOADING',
  fetchReviewSummary: 'fetchReviewSummary',
  fetchModelAccuracyScore: 'fetchModelAccuracyScore',
  exportIssuerCompliance: 'exportIssuerCompliance',
  compareAnswer: 'compareAnswer',
};

const hkex = {
  module: 'hkexModule',
};

const questionHKEX = {
  module: 'questionHKEXModule',
  SET_RULE_PROCESS: 'SET_RULE_PROCESS',
  SET_USER_NOTE: 'SET_USER_NOTE',
  SET_RULE_LIST: 'SET_RULE_LIST',
  SET_QUESTION_META: 'SET_QUESTION_META',
  SET_LOADING: 'SET_LOADING',
  fetchUserNotes: 'fetchUserNotes',
  updateUserNote: 'updateUserNote',
  createUserNote: 'createUserNote',
  fetchRuleList: 'fetchRuleList',
  fetchQuestionMeta: 'fetchQuestionMeta',
};

const schema = {
  module: 'schemaModule',
  TREENODE_CREATE: 'TREENODE_CREATE',
  TREENODE_UPDATE: 'TREENODE_UPDATE',

  // Schema
  SET_SCHEMAS: 'SET_SCHEMAS',
  SET_CUR_SCHEMA: 'SET_CUR_SCHEMA',
  SET_LOADING: 'SET_LOADING',
  SET_TRANSFER: 'SET_TRANSFER',
  fetchSchemas: 'fetchSchemas',
  saveSchema: 'saveSchema',
  fetchSchema: 'fetchSchema',
  updateSchema: 'updateSchema',
  deleteSchema: 'deleteSchema',
  persistSchemaType: 'persistSchemaType',
  removeSchemaType: 'removeSchemaType',
  persistSchemaEnum: 'persistSchemaEnum',
  fetchTransferData: 'fetchTransferData', // 获取schema迁移数据
  transferSchema: 'transferSchema', // schema迁移

  // Tree
  SET_SCHEMATREE_ID: 'SET_SCHEMATREE_ID',
  SET_SCHEMATREE_DATA: 'SET_SCHEMATREE_DATA',
  SET_SCHEMATREE_RESPONSE: 'SET_SCHEMATREE_RESPONSE',
  SET_PART_DATA: 'SET_PART_DATA',
  SET_EMPTYPART_DATA: 'SET_EMPTYPART_DATA',
  SET_FULLSCHEMA_DATA: 'SET_FULLSCHEMA_DATA',
  SET_CUR_ENTITY: 'SET_CUR_ENTITY',
  SET_TREE_ID: 'SET_TREE_ID',
  SET_TREE_LOADING: 'SET_TREE_LOADING',
  INSERT_EMPTY_NODE: 'INSERT_EMPTY_NODE', // 从父节点找
  CLEAR_EMPTY_NODE: 'CLEAR_EMPTY_NODE',
  TOGGLE_EMPTY_NODE: 'TOGGLE_EMPTY_NODE', // 从当前节点找
  fetchTreeData: 'fetchTreeData',
  updateTreeData: 'updateTreeData',
  persistSchemaPart: 'persistSchemaPart',
  persistSchemaWords: 'persistSchemaWords',
  openEditPopup: 'openEditPopup',
  persistTreeNode: 'persistTreeNode',
  deleteTreeNode: 'deleteTreeNode',
  moveTreeNode: 'moveTreeNode', // 调整tree node顺序
  saveRightAnswer: 'saveRightAnswer',
};

// schame type 枚举值
/**
 * 系统级枚举类型常量
 * schame (type)类型分三种：
 * - fixed, 系统级枚举，用户无法新增和修改；
 * - user，用户级枚举，用户可以增删改；
 * - normal，用户只能新增或者弃用，可以有子节点；
 */
const schemaDefaultType = '文本';
const schemaEnumType = [
  {
    label: '文本',
  },
  {
    label: '日期',
  },
  {
    label: '数字',
  },
];

const questionStatusNames = {
  prepare: 0,
  answering: 1,
  completed: 2,
  feedback: 3,
  conflict: 4,
  identical: 5,
  confirmed: 6,
};

/**
 * question_status 状态
 */
const questionStatus = {
  [questionStatusNames.prepare]: '待做',
  [questionStatusNames.answering]: '答题中',
  [questionStatusNames.completed]: '答题完毕',
  [questionStatusNames.feedback]: '已反馈',
  [questionStatusNames.conflict]: '答案不一致',
  [questionStatusNames.identical]: '答案一致',
  [questionStatusNames.confirmed]: '反馈已确认',
};

const SPLIT_SYMBOL = '|_|_|';

exports.SPLIT_SYMBOL = SPLIT_SYMBOL
