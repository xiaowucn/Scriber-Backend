const { schema, schemaDefaultType, schemaEnumType } = require('../store/constants');
const _ = require('lodash');

const sum = (a, b) => a + b;

const urlPrefix = '/api/v1';

const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function fetchJSON(url, params = {}) {
  let responseType = null;
  if (params.responseType) {
    responseType = params.responseType;
    delete params.responseType;
  } else {
    responseType = 'json';
  }
  // time out
  const res = await Promise.race([
    new Promise((resolve, reject) => {
      delay(30e3).then(() => {
        reject(new Error('timeout.'));
      });
    }),
    fetch(
      url,
      Object.assign(
        {
          credentials: 'include',
        },
        params,
      ),
    ),
  ]);
  if (res.status !== 200) {
    return Promise.reject(new Error(res.status + ''));
  }
  try {
    return await res[responseType]();
  } catch (e) {
    return Promise.reject(new Error('数据异常'));
  }
}

const getFileTypeByName = function(fileName = '') {
  if (typeof fileName !== 'string') {
    throw new TypeError('fileName must be a String.');
  }
  const index = fileName.lastIndexOf('.');
  if (index === -1) {
    // 没有后缀
    switch (fileName.toLowerCase()) {
      // intercept filename here...
      default: {
        return fileName;
      }
    }
  }
  const ext = fileName.substr(index + 1);
  return ext;
};

const yesOrNo = bool => {
  return bool ? '是' : '否';
};

const formatDateTime = ts => {
  if (typeof ts !== 'number') {
    return '';
  }
  if (ts.toString().length <= 10) {
    ts = ts * 1000;
  }
  const dt = new Date(ts);
  const date = [];
  date.push(dt.getFullYear());
  date.push(dt.getMonth() < 9 ? '0' + (dt.getMonth() + 1) : dt.getMonth() + 1);
  date.push(dt.getDate() < 10 ? '0' + dt.getDate() : dt.getDate());
  const time = [];
  time.push(dt.getHours() < 10 ? '0' + dt.getHours() : dt.getHours());
  time.push(dt.getMinutes() < 10 ? '0' + dt.getMinutes() : dt.getMinutes());
  time.push(dt.getSeconds() < 10 ? '0' + dt.getSeconds() : dt.getSeconds());
  return date.join('-') + ' ' + time.join(':');
};

const parseIntNumber = num => {
  return Math.round(num * 100) + '%';
};

const getCount = (() => {
  let count = 0;
  return function() {
    return ++count;
  };
})();

const convertFileTypeToIcon = function(fileType = '') {
  if (typeof fileType !== 'string') {
    throw new TypeError('fileType must be a String.');
  }
  const clazz = ['far'];
  switch (fileType.toLowerCase()) {
    case 'heic':
    case 'webp':
    case 'gif':
    case 'bmp':
    case 'png':
    case 'jpeg':
    case 'jpg': {
      clazz.push('file-image');
      break;
    }
    case 'acc':
    case 'wav':
    case 'wma':
    case 'mp3': {
      clazz.push('file-audio');
      break;
    }
    case 'mkv':
    case 'avi':
    case 'mp4': {
      clazz.push('file-video');
      break;
    }
    case '7z':
    case 'tar':
    case 'gz':
    case 'rar':
    case 'zip': {
      clazz.push('file-archive');
      break;
    }
    case 'md':
    case 'txt': {
      clazz.push('file-alt');
      break;
    }
    case 'js':
    case 'java':
    case 'py':
    case 'go':
    case 'c': {
      clazz.push('file-code');
      break;
    }
    case 'pdf': {
      clazz.push('file-pdf');
      break;
    }
    case 'docx':
    case 'doc': {
      clazz.push('file-word');
      break;
    }
    case 'xlsx':
    case 'xls': {
      clazz.push('file-excel');
      break;
    }
    case 'ppt':
    case 'pptx': {
      clazz.push('file-powerpoint');
      break;
    }
    case 'parent': {
      clazz.push('folder-open');
      break;
    }
    case 'folder': {
      clazz.push('folder');
      break;
    }
    case 'license': {
      clazz.push('info-circle');
      break;
    }
    default: {
      clazz.push('file');
    }
  }
  clazz[1] = 'fa-' + clazz[clazz.length - 1];
  clazz.push('fa-2x', 'fa-fw');
  return clazz.join(' ');
};

/**
 * 使用Promise来包裹 Element UI 的表单校验
 */
function validateToPromise($form) {
  return new Promise(resolve => {
    $form.validate(valid => resolve(valid));
  });
}

/**
 * 创建空的Schema对象
 * @param {String} name
 */
function createEmptyFullSchema(name = '') {
  return {
    name,
    data: {
      schemas: [
        {
          name,
          schema: [],
        },
      ],
      schema_types: [],
    },
  };
}

/**
 * 将 EntityData 转换为 SchemaData
 * @param {Object} schema
 */
function fullEntityToSchema(entity, rootSchemaWords) {
  return Object.assign(
    {
      id: entity.id,
      created_utc: entity.created_utc,
      name: entity.name,
      updated_utc: entity.updated_utc,
      checksum: entity.checksum,
    },
    {
      data: entityToSchema(entity.data || {}, entity.words || rootSchemaWords),
    },
  );
}

/**
 * 将 EntityData 转换为 SchemaData (转换data)
 * @param {Array} entityData
 */
function entityToSchema(entity, words) {
  if (!entity.top) {
    throw new TypeError("the schema's part of Top can't be null.");
  }
  return {
    schemas: [
      trimEntityData(entity.top, words),
      ...entity.normals.map(normal => trimEntityData(normal)),
    ],
    schema_types: entity.schemaTypes || [],
  };
}

// 定义数据结构
function trimEntityData(entityData, words) {
  const orders = entityData.attrs.map(attr => attr.name);
  const schema = (entityData.attrs || []).reduce((a, v) => {
    a[v.name] = {
      type: v.type,
      required: v.required,
      multi: v.multi,
      words: v.words,
    };
    return a;
  }, {});
  return { name: entityData.name, orders, schema, words };
}

/**
 * 将 SchemaData 转换为 EntityData
 * @param {Object} schema
 */
function fullSchemaToEntity(schema) {
  return Object.assign(
    {
      _index: getCount(),
      id: schema.id,
      created_utc: schema.created_utc,
      name: schema.name,
      updated_utc: schema.updated_utc,
      checksum: schema.checksum,
    },
    {
      data: schemaToEntity(schema.data || {}),
    },
  );
}

/**
 * 将 SchemaData 转换为 EntityData (转换data)
 * @param {Array} schemaData
 */
function schemaToEntity(schemaData) {
  const data = schemaData.schemas || schemaData;
  if (data.length === 0) {
    throw new TypeError("the schemas's length must more than 0.");
  }
  return {
    top: trimSchemaData(data[0]),
    normals: data.slice(1).map(schema => trimSchemaData(schema)),
    schemaTypes: _.isArray(schemaData.schema_types)
      ? schemaData.schema_types.slice()
      : [],
  };
}
function trimSchemaData(schemaData) {
  const orders = _.isArray(schemaData.orders)
    ? schemaData.orders
    : Object.keys(schemaData.schema);
  let result = {
    _index: getCount(),
    name: schemaData.name,
    orders,
    attrs: orders.map(name =>
      Object.assign(schemaData.schema[name], { name, _index: getCount() }),
    ),
  };
  if (schemaData.words) {
    result.words = schemaData.words;
  }
  return result;
}

/**
 * 将 schema 转换为 tree 对象
 * 需注意：
 * 由于schema.type 是引用类型，所以一个 tree item 可能会
 * 存在于多个tree node 中，一处 tree item 改变，会引发
 * 所有 tree item 改变
 * @param {Object} schema
 */
function parseEntityToTree(entity) {
  const types = getAllTypesFromEntity(entity);
  entity = entity.data;
  const subSchemas = {};
  for (let i = 0; i < entity.normals.length; i++) {
    for (let j = 0; j < entity.normals[i].attrs.length; j++) {
      subSchemas[entity.normals[i].attrs[j].name] = Object.assign(
        {},
        entity.normals[i].attrs[j],
        {
          _parentSchema: {
            name: entity.normals[i].name,
          },
          _topSchema: {
            name: entity.top.name,
          },
        },
      );
    }
  }
  const result = {
    // entities: {
    //   attrs: subSchemas,
    //   normals: entity.normals
    // },
    relations: {
      tree: {
        meta: {
          _index: entity.top._index,
          _partType: 'root',
          _type: {
            label: entity.top.name,
            type: 'group',
          },
        },
        data: {
          label: entity.top.name,
          type: entity.top.name,
          words: entity.top.words,
        },
        children: createTreeItem(entity.top, entity.normals, types),
      },
    },
  };
  return result;
}

function createTreeItem(top, normals, types = []) {
  let root = [];
  let queue = [];
  top.attrs.forEach(attr => {
    root.push({
      data: {
        label: attr.name,
        type: attr.type,
        required: attr.required,
        multi: attr.multi,
        words: attr.words || '',
      },
      meta: {
        _path: [attr.name],
        _index: attr._index,
        _partType: 'top',
        _type: getSchemaType(types, attr.type),
      },
      children: [],
    });
  });
  queue = root.slice();
  while (queue.length > 0) {
    const unit = queue.shift();
    if (unit.data.type && unit.data.type !== 'text') {
      // 查找子
      const subSchema = getSubSchemas(unit.data.type, normals);
      if (!subSchema) {
        continue;
      }
      const children = subSchema.children;
      for (let i = 0; i < children.length; i++) {
        const child = {
          data: {
            // ...children[i],
            label: children[i].name,
            required: children[i].required,
            multi: children[i].multi,
            type: children[i].type,
            words: children[i].words || '',
          },
          meta: {
            _index: children[i]._index,
            _path: [...unit.meta._path, unit.data.type],
            _partType: 'normal.schema',
            _type: getSchemaType(types, children[i].type),
          },
          children: [],
        };
        unit.children.push(child);
        queue.push(child);
      }
    }
  }
  return root;
}
/**
 * 从top遍历每一个item
 * @param {Object} entity entity对象
 * @param {String} name 开始的名称，为null表示从top开始遍历
 * @param {Function} callback 回调
 * @param {number} count 计数
 */
function eachEntityItem(entity, name, callback, count = 0) {
  if (name === null) {
    name = entity.data.top.name;
  }
  const allSchemas = entity.data.normals.concat([entity.data.top]);
  const schemaType = allSchemas.find(scm => scm.name === name);
  if (count > 1000) {
    throw new Error('schemas type has a loop.');
  }
  if (!schemaType) {
    return null;
  }
  for (let i = 0; i < schemaType.attrs.length; i++) {
    const attr = schemaType.attrs[i];
    callback(attr, schemaType);
    count += 1;
    eachEntityItem(entity, attr.name, callback, count);
  }
}

function getSubSchemas(name, normals) {
  const schemaData = normals.find(normal => normal.name === name);
  if (schemaData) {
    return {
      parent: schemaData,
      children: (schemaData.attrs && schemaData.attrs.slice()) || [],
    };
  } else {
    return null;
  }
}

function pdfParseStatus(status) {
  switch (status) {
    case 1:
      return '排队中';
    case 2:
      return '解析中';
    case 3:
      return '已取消';
    case 4:
      return '完成';
    case 5:
      return '失败';
    default:
      return '';
  }
}

function pdfPresetAnswerStatus(status) {
  switch (status) {
    case true:
      return '已完成';
    case false:
      return '未完成';
    default:
      return '';
  }
}

function fileSize(bytes) {
  if (typeof bytes !== 'number') {
    return '';
  }
  const MB = Math.pow(1024, 2);
  if (bytes > MB) {
    return (bytes / MB).toFixed(2) + ' MB';
  }
  return (bytes / 1024).toFixed(2) + ' KB';
}

/**
 * 获取dom距离浏览器顶部和左侧的距离
 * @param {Dom} elem
 */
function getDomOffset(elem) {
  if (!elem.getClientRects().length) {
    return { top: 0, left: 0 };
  }
  const rect = elem.getBoundingClientRect();
  const win = elem.ownerDocument.defaultView;
  return {
    top: rect.top + win.pageYOffset,
    left: rect.left + win.pageXOffset,
  };
}

/**
 * 通过 index 找到schemaPart，并返回这个对象的引用
 * @param {Number} index
 * @param {Object} full
 * @returns {{partType: String, items: Array<Object>}}
 */
function getSchemaPartByIndex(index, full) {
  let inx = -1;
  // 顶级schema
  if (full.top._index === index) {
    return {
      partType: 'top',
      items: [full.top],
    };
  } else if (
    (inx = full.top.attrs.findIndex(attr => attr._index === index)) !== -1
  ) {
    return {
      partType: 'top.schema',
      items: [full.top.attrs[inx], full.top],
    };
  } else if (
    (inx = full.normals.findIndex(normal => normal._index === index)) !== -1
  ) {
    return {
      partType: 'normal',
      items: [full.normals[inx], full.normals],
    };
  } else {
    for (let i = 0; i < full.normals.length; i++) {
      for (let j = 0; j < full.normals[i].attrs.length; j++) {
        const attr = full.normals[i].attrs[j];
        if (attr._index === index) {
          return {
            partType: 'normal.schema',
            items: [attr, full.normals[i]],
          };
        }
      }
    }
    throw new Error(`not found children by index=${index}.`);
  }
}
/**
 * 找到指定 key (默认是meta._index)的node，并返回引用；找不到时返回undefined
 * @param {Object} treeData
 * @param {Number} value
 */
function getNodeInTreeData(treeData, value, key = 'meta._index') {
  if (!treeData) {
    return;
  }
  let [target] = _.at(treeData, key);
  if (target === value) {
    return treeData;
  } else if (treeData.children) {
    for (let i = 0; i < treeData.children.length; i++) {
      const result = getNodeInTreeData(treeData.children[i], value, key);
      if (result) {
        return result;
      }
    }
  }
}
/**
 * 找到指定 key (默认是meta._index)的node，并返回引用；找不到时返回undefined
 * @param {Object} treeData
 * @param {Number} value
 */
function getNodeInTreeParent(treeData, value, key = 'meta._index') {
  if (!treeData) {
    return;
  }
  let [target] = _.at(treeData, key);
  if (target === value) {
    return treeData;
  } else if (treeData.children) {
    for (let i = 0; i < treeData.children.length; i++) {
      const result = getNodeInTreeParent(treeData.children[i], value, key);
      if (result) {
        return treeData.children[i];
      }
    }
  }
}

/**
 * 深度遍历树节点
 * @param {Object} treeNode 树的根节点
 * @param {Function} callback 遍历节点时的回调函数，参数有 node, parent，根node没有parent
 * @param {Object} parent 内部调用传参，初始调用时不需要传值
 */
function eachTreeNode(treeNode, callback, parent = null) {
  const result = callback(treeNode, parent);
  if (result === false) {
    return;
  }
  const children = (treeNode && treeNode.children) || [];
  for (let i = 0; i < children.length; i++) {
    eachTreeNode(children[i], callback, treeNode);
  }
}

/**
 * 创建一个空的树节点
 */
function createEmptyTreeNode() {
  return {
    meta: {
      _mode: schema.TREENODE_CREATE, // create or update
      _index: -1,
      _nodeIndex: -1,
      _path: [],
    },
    data: {
      name: '',
      type: schemaDefaultType,
      required: false,
      multi: false,
    },
  };
}

/**
 * @param {Array} arr
 * @param {Number} oldIndex
 * @param {Number} newIndex
 */
function arrayMove(arr, oldIndex, newIndex) {
  if (newIndex === oldIndex) {
    return arr;
  }
  var tmp = arr.splice(oldIndex, 1);
  arr.splice(newIndex, 0, tmp[0]);
  return arr;
}

/**
 * 获得枚举/基本类型，如果找不到返回null
 * @param {Array} types 类型数组
 * @param {String} type 类型名称
 */
const getSchemaType = (types, type) => {
  const basicTypes = types.filter(t => t.type === 'basic');
  const enumTypes = types.filter(t => t.type === 'enum');
  const groupTypes = types.filter(t => t.type === 'group');
  // 对于系统枚举类型需要进行大小写过滤
  for (let i = 0; i < basicTypes.length; i++) {
    if (basicTypes[i].label.toUpperCase() === type.toUpperCase()) {
      return basicTypes[i];
    }
  }
  // 对于用户创建的类型直接比较
  for (let i = 0; i < enumTypes.length; i++) {
    if (enumTypes[i].label === type) {
      return enumTypes[i];
    }
  }
  // 判断是否是组合类型
  for (let i = 0; i < groupTypes.length; i++) {
    if (groupTypes[i].label === type) {
      return groupTypes[i];
    }
  }
  return null;
};
/**
 * 从Entity中获取所有类型，包括basic/enum/group
 * @param {Entity} entity
 */
const getAllTypesFromEntity = entity => {
  const basicTypes = _.map(schemaEnumType, v =>
    Object.assign(v, { type: 'basic' }),
  );
  const normalTypes = _.map(entity && entity.data.normals, normal => ({
    label: normal.name,
    type: 'group',
  }));
  return [
    ...basicTypes,
    ...entity.data.schemaTypes.map(t => Object.assign(t, { type: 'enum' })),
    ...normalTypes,
  ];
};

/**
 * Scrolls specified element into view of its parent.
 * @param {Object} element - The element to be visible.
 * @param {Object} spot - An object with optional top and left properties,
 *   specifying the offset from the top left edge.
 * @param {boolean} skipOverflowHiddenElements - Ignore elements that have
 *   the CSS rule `overflow: hidden;` set. The default is false.
 */
const scrollIntoView = function(
  element,
  spot,
  skipOverflowHiddenElements = false,
) {
  // Assuming offsetParent is available (it's not available when viewer is in
  // hidden iframe or object). We have to scroll: if the offsetParent is not set
  // producing the error. See also animationStarted.
  let parent = element.offsetParent;
  if (!parent) {
    console.error('offsetParent is not set -- cannot scroll');
    return;
  }
  let offsetY = element.offsetTop + element.clientTop;
  let offsetX = element.offsetLeft + element.clientLeft;
  while (
    (parent.clientHeight === parent.scrollHeight &&
      parent.clientWidth === parent.scrollWidth) ||
    (skipOverflowHiddenElements &&
      getComputedStyle(parent).overflow === 'hidden')
  ) {
    if (parent.dataset._scaleY) {
      offsetY /= parent.dataset._scaleY;
      offsetX /= parent.dataset._scaleX;
    }
    offsetY += parent.offsetTop;
    offsetX += parent.offsetLeft;
    parent = parent.offsetParent;
    if (!parent) {
      return; // no need to scroll
    }
  }
  if (spot) {
    if (spot.top !== undefined) {
      offsetY += spot.top;
    }
    if (spot.left !== undefined) {
      offsetX += spot.left;
      parent.scrollLeft = offsetX;
    }
  }
  parent.scrollTop = offsetY;
};

/**
 * 在treeData中增加_mate的parent等属性，修改tree本身
 * @param {Object} tree
 */
const initTreeData = tree => {
  let nodeIndex = 1e3;
  eachTreeNode(tree, (node, parent) => {
    nodeIndex += 1;
    Object.assign(node.meta, {
      _isHide: false,
      _nodeIndex: nodeIndex,
    });
    if (parent) {
      Object.assign(node.meta, {
        _parent: parent.meta._parent.concat([parent.data.label]),
        _path: [...parent.meta._path, node.data.type],
      });
    } else {
      Object.assign(node.meta, {
        _parent: [],
        _path: [node.data.type],
      });
    }
  });
};

exports.fullSchemaToEntity = fullSchemaToEntity
exports.parseEntityToTree = parseEntityToTree
exports.initTreeData = initTreeData
exports.eachTreeNode = eachTreeNode
