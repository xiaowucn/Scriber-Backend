const _ = require('lodash');

const SPLIT_SYMBOL = '|_|_|';
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

/**
 * fn([ab,c], [x, y, z] )-> [[x, y], z]
 * 按照标签列表的每一项，生成text属性一致的组，详情见单元测试
 * @param {Array<string>} labels 标签列表
 * @param {Array<Object>} items 项目列表，text属性对应label
 */
function splitLabels(labels, items) {
  const result = labels.map(() => []);
  let itemIndex = 0;
  for (let i = 0; i < labels.length; i++) {
    const label = labels[i];
    for (let j = itemIndex; j < items.length; j++) {
      const subItems = items.slice(itemIndex, j + 1);
      const subName = subItems.map(itm => itm.text).join('');
      if (subName === label) {
        itemIndex = j + 1;
        result[i].push(...subItems);
        break;
      }
    }
  }
  return result;
}

/**
 * 组合类型节点包含多个答案
 * @param {*} field
 */
function createFieldOfGroup(field) {
  const labels = field.label.split(SPLIT_SYMBOL);
  const children = splitLabels(labels, field.components);
  return children.map(list => {
    const boxes = list.map(itm => parseBoxToV2(itm));
    return {
      boxes,
      handleType: 'wireframe',
    };
  });
}
/**
 * 是否所有的key都是indexKey（每一行答案中的key，转换为数组后，每一项的末尾都有:index）
 * @param {Array} allKeys
 */
 function isValidAllIndexKeys(allKeys) {
  return allKeys.every(rawKey => {
    const key = rawKeyToArray(rawKey);
    return key.every(keyPart => /:\d+$/.test(keyPart));
  });
}
const getCounterGenerate = (start = 0) => {
  return function() {
    return ++start;
  };
};
const getCounter = getCounterGenerate();

/**
 * 将字符串、数组格式的key都转换为数组
 */
function rawKeyToArray(rawKey) {
  if (_.isString(rawKey)) {
    return JSON.parse(rawKey);
  } else if (_.isArray(rawKey)) {
    return rawKey;
  }
  throw new TypeError(`不支持的key格式（${rawKey}）`);
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
    _index: getCounter(),
    name: schemaData.name,
    orders,
    attrs: orders.map(name =>
      Object.assign(schemaData.schema[name], { name, _index: getCounter() }),
    ),
  };
  if (schemaData.words) {
    result.words = schemaData.words;
  }
  return result;
}
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
 * 将 schema 转换为 tree 对象
 * 需注意：
 * 由于schema.type 是引用类型，所以一个 tree item 可能会
 * 存在于多个tree node 中，一处 tree item 改变，会引发
 * 所有 tree item 改变
 * @param {Object} entity
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
 * 在treeData中增加_mate的parent等属性，修改tree本身
 * @param {Object} tree
 */
function initTreeData(tree) {
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
 * 扁平化schema的数据结构
 * @param {Object} schema
 */
function flattenSchemaData(schema) {
  let flattenSchema = [];
  let originSchema = _.cloneDeep(schema);
  let entity = schemaToEntity(originSchema);
  let { relations } = parseEntityToTree({ data: entity });
  initTreeData(relations.tree);
  eachTreeNode(relations.tree, node => {
    flattenSchema.push(node);
  });
  return flattenSchema;
}
/**
 * 判断schema节点是否具有答案
 * @param {Object} answer 用户答案
 */
function hasNodeAnswer(answer) {
  let hasAnswer = false;
  if (!answer.label) {
    return hasAnswer;
  } else if (answer.items && answer.items.length > 0) {
    answer.items.forEach(item => {
      if (item.enumLabel) {
        hasAnswer = true;
      } else {
        item.fields.forEach(field => {
          if (
            (field.components && field.components.length > 0) ||
            field.enumLabel
          ) {
            hasAnswer = true;
          }
        });
      }
    });
  }
  return hasAnswer;
}
function getSchemaByKey(pathKey, flattenSchema) {
  let currentLabel = _.last(pathKey);
  return flattenSchema.find(item => {
    let itemKey = JSON.stringify([...item.meta._parent, item.data.label]);
    return (
      item.data.label === currentLabel && JSON.stringify(pathKey) === itemKey
    );
  });
}
/**
 * 生成答案唯一key
 * @param {*} path 当前节点路径
 * @param {*} index 当前节点index
 */
function createNodeKey(path, index) {
  path.splice(0, 1, `${path[0]}:0`);
  if (typeof index !== 'undefined') {
    path.splice(1, 1, `${path[1]}:${index}`);
    path.splice(2, 1, `${path[2]}:0`);
  } else {
    path.splice(1, 1, `${path[1]}:0`);
  }
  return path;
}
/**
 * 检测某条答案是否只选择了选框，适用于v1
 * @param {Object} answerItem
 */
function isOnlyEnumSelectedV1(answerItem) {
  return answerItem.fields.length === 0 && answerItem.enumLabel;
}
/**
 * 针对v1答案中，如果先画框，后选枚举值，items中会出现两条信息的问题，将这两条信息合并为一条信息
 * @param {Array} items
 */
function mergeAnswerItems(items) {
  if (items.length === 0) return items.slice();
  let fields = [];
  let enumLabel = '';
  for (let i = 0; i < items.length; i++) {
    if (items[i].fields.length !== 0) {
      fields.push(...items[i].fields);
    }
    if (typeof items[i].enumLabel === 'string') {
      enumLabel = items[i].enumLabel;
    }
  }
  return Object.assign({}, ...items, { fields, enumLabel });
}
/**
 * 生成V2答案项只有枚举值无画框答案
 * @param {string} key
 * @param {*} schema 和当前field相关的schemaItem
 * @param {*} data 当前节点答案画框数据
 * @param {*} enumLabel 枚举的值
 */
function createAnswerItem(key, schema, enumLabel, data = []) {
  let nodeSchema = {
    data: schema.data,
  };
  return { key, schema: nodeSchema, data, value: enumLabel };
}
/**
 * 生成答案个数（画框数据）
 * @param {*} components
 */
function createFieldItem(components) {
  const boxes = components.map(itm => parseBoxToV2(itm));
  return {
    boxes,
    handleType: 'wireframe',
  };
}
/**
 * 组合类型的子节点是否只勾选了枚举值
 * @param {string} field
 */
function isJustEnumSelected(field) {
  return field.components.length === 0 && field.enumLabel;
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
  if (!treeNode) return null;
  if (_.isArray(treeNode.childrenGroup)) {
    for (let i = 0; i < treeNode.childrenGroup.length; i++) {
      const nodeGroup = treeNode.childrenGroup[i];
      for (let j = 0; j < nodeGroup.length; j++) {
        eachTreeNode(nodeGroup[j], callback, treeNode);
      }
    }
  } else {
    const children = treeNode.children || [];
    for (let i = 0; i < children.length; i++) {
      eachTreeNode(children[i], callback, treeNode);
    }
  }
}

/**
 * 将用户答案v1扁平化并转换为v2.2
 * @param {Object} v1Answer 用户答案
 * @param {Object} schema Schema
 */
function parseAnswerToV2_2(v1Answer, schema) {
  let flattenSchema = flattenSchemaData(schema);
  const v2Answers = [];
  _.forEach(v1Answer, function(answer) {
    if (!hasNodeAnswer(answer)) return;
    let rootLabel = flattenSchema[0].data.label;
    let pathKey = [rootLabel, answer.label];
    let schema = getSchemaByKey(pathKey, flattenSchema);
    if (schema === null) {
      throw new TypeError(`The '${pathKey}' answer without schema.`);
    }
    // answer分为单个节点和组合类型节点
    if (schema.children.length === 0) {
      let key = JSON.stringify(createNodeKey(pathKey));
      let answerItems = mergeAnswerItems(answer.items);
      let isJustEnumSelected = isOnlyEnumSelectedV1(answerItems);
      // 只勾选了枚举值
      let enumVal = answerItems.enumLabel || null;
      if (isJustEnumSelected) {
        let item = createAnswerItem(key, schema, enumVal);
        v2Answers.push(item);
      } else {
        let data = answerItems.fields.map(field => {
          return createFieldItem(field.components);
        });
        let item = createAnswerItem(key, schema, enumVal, data);
        v2Answers.push(item);
      }
    } else {
      // 组合类型节点
      answer.items.forEach((group, index) => {
        group.fields.forEach(field => {
          let childrenKey = pathKey.slice();
          childrenKey.push(`${field.name}`);
          let nodeSchema = getSchemaByKey(childrenKey, flattenSchema);
          let key = JSON.stringify(createNodeKey(childrenKey, index));
          if (field.components.length === 0 && !field.enumLabel) return;
          let enumVal = field.enumLabel || null;
          const isOnlyEnum = isJustEnumSelected(field);
          // 只勾选了枚举值
          if (isOnlyEnum) {
            let item = createAnswerItem(key, nodeSchema, enumVal);
            v2Answers.push(item);
          } else {
            // 当前叶子节点只有一条答案
            if (field.label.indexOf(SPLIT_SYMBOL) === -1) {
              let data = [createFieldItem(field.components)];
              let item = createAnswerItem(key, nodeSchema, enumVal, data);
              v2Answers.push(item);
            } else {
              // 当前叶子节点有多条答案
              let data = createFieldOfGroup(field);
              let item = createAnswerItem(key, nodeSchema, enumVal, data);
              v2Answers.push(item);
            }
          }
        });
      });
    }
  });
  return {
    items: v2Answers,
    version: '2.2',
  };
}
function parseBoxToV2(v1Box) {
  try {
    const { top, left, width, height, page } = v1Box.frameData;
    return {
      box: {
        box_left: Number(left),
        box_top: Number(top),
        box_right: Number(left) + Number(width),
        box_bottom: Number(top) + Number(height),
      },
      page,
      text: v1Box.text,
    };
  } catch (error) {
    throw error;
  }
}
/**
 * 如果用户答案不是每一项都追加了:index的答案，那么为每一项答案的key都加上:0
 * @param {Array} answers2_0 用户答案
 */
function parseAnswerV2_0ToV2_2(answers2_0) {
  for (let i = 0; i < answers2_0.length; i++) {
    const answer = answers2_0[i];
    if (!isValidAllIndexKeys([answer.key])) {
      const keys = JSON.parse(answer.key);
      for (let j = 0; j < keys.length; j++) {
        keys[j] = keys[j] + ':0';
      }
      answer.key = JSON.stringify(keys);
    }

    // v2.2 变动：value 值挪到和 data 同级
    if (answer.value === undefined) {
      let enumValue = undefined;
      for (let j = 0; j < answer.data.length; j++) {
        const data = answer.data[j];
        if (data.value) {
          enumValue = data.value;
          break;
        }
      }
      if (enumValue) {
        answer.value = enumValue;
      }
    }

    // data.box 为空则将 data 置为 []
    for (let j = answer.data.length - 1; j >= 0; j--) {
      if (answer.data[j].boxes.length == 0) {
        answer.data.pop(j);
      }
    }
  }
  return answers2_0;
}

module.exports = {
  parseAnswerV1_0ToV2_2: parseAnswerToV2_2,
  parseAnswerV2_0ToV2_2,
};
