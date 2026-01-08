var _ = require('lodash');
var md5 = require('blueimp-md5');
var {
  fullSchemaToEntity,
  parseEntityToTree,
  initTreeData,
  eachTreeNode,
} = require('.');
var { SPLIT_SYMBOL } = require('../store/constants');

/**
 * 按照标签列表的每一项，生成text属性一致的组
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
 * 将用户答案v1扁平化并转换为v2
 * @param {Object} v1Answer 用户答案
 * @param {Object} schema Schema类型
 */
function parseAnswerToV2(v1Answer, schema) {
  const entity = fullSchemaToEntity(schema);
  const { relations } = parseEntityToTree(entity);
  const items = [];
  // 增加schema_item的额外属性（meta._parents）
  initTreeData(relations.tree);
  _.forEach(v1Answer, function(answer) {
    const parents = answer.schemaPath.slice();
    const key = JSON.stringify(parents);
    let schema = null;
    eachTreeNode(relations.tree, function(node) {
      const nodePath = JSON.stringify(
        node.meta._parent.slice().concat(node.data.label),
      );
      if (nodePath === JSON.stringify(parents)) {
        schema = node;
        return false;
      }
    });
    if (schema === null) {
      throw new TypeError(`The '${key}' answer without schema.`);
    }
    let schemaAttrs = {};
    if (parents.length !== 1) {
      // root schema item
      schemaAttrs = {
        multiple: schema.data.multi, // schema attribute name is multi
        required: schema.data.required,
      };
    }
    schema = {
      data: {
        label: schema.data.label,
        type: schema.data.type,
        // TODO: just for unit test. don't delete.
        words: schema.data.words || '',
      },
      meta: removeSchemaIdentity(schema.meta),
      children: schema.children,
    };
    Object.assign(schema.data, schemaAttrs);
    const item = {
      key,
      schema,
      data: [],
    };
    items.push(item);
    mergeAnswerItems(answer.items);
    // 为每个子项生成schema_item
    if (answer.items[0] && answer.items[0].fields) {
      if (schema.meta._type.type !== 'group') {
        // 如果子项是基本、枚举类型，将子项作为标记内容
        for (let i = 0; i < answer.items[0].fields.length; i++) {
          const field = answer.items[0].fields[i];
          const enumLabel = answer.items[0].enumLabel;
          // const key = JSON.stringify(parents.concat(field.name));
          const fieldItem = createFieldItem(key, field, schema, enumLabel);
          item.data.push(...fieldItem.data);
        }
        return;
      }
      // 如果子项是组合类型，将子项提到外层，子项具有独立的key，可作为规则索引
      for (let i = 0; i < answer.items[0].fields.length; i++) {
        const field = answer.items[0].fields[i];
        const enumLabel = answer.items[0].enumLabel;
        const key = JSON.stringify(parents.concat(field.name));
        let schema = null;
        eachTreeNode(relations.tree, function(node) {
          const nodePath = JSON.stringify(
            node.meta._parent.concat(node.data.label),
          );
          if (nodePath === key) {
            schema = node;
            return false;
          }
        });
        if (!schema) continue;
        const fieldItem = createFieldItem(key, field, schema, enumLabel);
        items.push(fieldItem);
      }
    }
  });
  return { items };
}
function createFieldItem(key, field, schema, enumLabel) {
  const labels = field.label.split(SPLIT_SYMBOL);
  const children = splitLabels(labels, field.components);
  return {
    key,
    schema: {
      data: {
        label: schema.data.label,
        multiple: schema.data.multi, // origin schema is multi
        required: schema.data.required,
        type: schema.data.type,
        // TODO: just for unit test. don't delete.
        words: schema.data.words || '',
      },
      meta: removeSchemaIdentity(schema.meta),
      children: schema.children.map(child => ({
        data: child.data,
        meta: removeSchemaIdentity(child.meta),
      })),
    },
    data: children.map(list => {
      const boxes = list.map(itm => parseBoxToV2(itm));
      return {
        boxes,
        value: enumLabel,
        handleType: 'wireframe',
      };
    }),
  };
}

function collectOtherItems(listedItems, otherItems) {
  for (let i = 0; i < listedItems.length; i++) {
    const listedItem = listedItems[i];
    let children = getChildren(listedItem.key, otherItems);
    Object.assign(listedItem, {
      otherItems: children,
    });
  }
  function getChildren(key, otherItems) {
    let children = [];
    for (let i = 0; i < otherItems.length; i++) {
      const item = otherItems[i];
      if (item.key.startsWith(key.slice(0, -1))) {
        children.push(item);
      }
    }
    return children;
  }
}
function createBaseItem(items, tree) {
  const baseItems = [];
  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    const isGrp = item.schema.meta._type.type === 'group';
    const level = JSON.parse(item.key).length;
    if (level <= 2 || isGrp) {
      baseItems.push(item);
    } else {
      const keys = JSON.parse(item.key);
      const parentKey = keys.slice(0, 2);
      if (!hasInBaseItem(parentKey, baseItems)) {
        baseItems.push(createAnswerItemV1(parentKey, tree));
      }
    }
  }
  return baseItems;
}
function createAnswerItemV1(key, tree) {
  return {
    key: JSON.stringify(key),
    schema: getSchemaWithKey(key, tree),
    data: [],
  };
}
function getSchemaWithKey(key, tree) {
  let schema = null;
  eachTreeNode(tree, function(node) {
    const nodePath = JSON.stringify(
      node.meta._parent.slice().concat(node.data.label),
    );
    if (nodePath === JSON.stringify(key)) {
      schema = node;
      return false;
    }
  });
  return schema;
}
function hasInBaseItem(key, items) {
  if (_.isArray(key)) {
    key = JSON.stringify(key);
  }
  return !_.isNil(_.find(items, itm => itm.key === key));
}
/**
 * 部分规则:
 * 0. 根节点没有 items 和 attributes
 * 1. schema树在展示时，只显示 层级小于等于2的类型 和 组合类型
 * 2. 答案的attribute中只存储type !== 'group'的schema类型
 */
function parseAnswerToV1(v2Answer, fullSchema) {
  fullSchema = _.cloneDeep(fullSchema);
  const entity = fullSchemaToEntity(fullSchema);
  const { relations } = parseEntityToTree(entity);
  // 增加schema_item的额外属性（meta._parents）
  initTreeData(relations.tree);
  const items = _.cloneDeep(v2Answer.items);
  const listedItems = createBaseItem(items, relations.tree);
  const otherItems = _.xor(listedItems, items);
  collectOtherItems(listedItems, otherItems);
  const result = {};
  for (let i = 0; i < listedItems.length; i++) {
    const answer = listedItems[i];
    const md5str = md5(answer.key);

    const children = answer.otherItems;
    const schemaType = answer.schema.meta._type.type;
    const attributes = [];
    const items = [];
    if (schemaType !== 'group') {
      attributes.push(trimSchemaItem(answer.schema.data));
      for (let j = 0; j < answer.data.length; j++) {
        const answerData = answer.data[j];
        const item = {
          fields: [
            {
              components: answerData.boxes.map(box => {
                const result = {
                  frameData: parseBoxToV1(box, answer.schema.data),
                  text: box.text,
                };
                return result;
              }),
              name: answer.schema.data.label,
              label: answerData.boxes
                .map(component => component.text)
                .join(SPLIT_SYMBOL),
            },
          ],
          schemaMD5: md5str,
        };
        if (typeof answerData.value === 'string') {
          Object.assign(item, {
            enumLabel: answerData.value,
          });
        }
        items.push(item);
      }
    } else {
      // root schema item items 为 []
      if (answer.schema.meta._partType !== 'root') {
        let fields = children.map(child => {
          const components = [];
          for (let k = 0; k < child.data.length; k++) {
            const answerItem = child.data[k];
            for (let j = 0; j < answerItem.boxes.length; j++) {
              const box = answerItem.boxes[j];
              const component = {
                frameData: parseBoxToV1(box, child.schema.data),
                text: box.text,
              };
              components.push(component);
            }
          }
          return {
            components,
            label: child.data
              .map(answerItem => answerItem.boxes.map(box => box.text).join(''))
              .join(SPLIT_SYMBOL),
            enumLabel: child.data.length !== 0 && child.data[0].value,
            name: child.schema.data.label,
            type: child.schema.data.type,
          };
        });

        if (fields.length > 0) {
          items.push({
            fields,
            schemaMD5: md5str,
          });
        }
        attributes.push(
          ...answer.schema.children
            .filter(childSchema => childSchema.meta._type.type !== 'group')
            .map(child => ({
              multiple: child.data.multi,
              name: child.data.label,
              required: child.data.required,
              type: child.data.type,
            })),
        );
      }
    }
    result[md5str] = Object.assign({}, answer.schema.data, {
      attributes,
      items,
      label: answer.schema.data.label,
      md5: md5str,
      schemaPath: JSON.parse(answer.key),
      type: answer.schema.data.type,
    });
  }
  return result;
}
function trimSchemaItem(item) {
  return {
    multiple: item.multiple,
    name: item.label,
    required: item.required,
    type: item.type,
  };
}
function removeSchemaIdentity(item) {
  delete item['_index'];
  delete item['_nodeIndex'];
  return item;
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
 * 针对v1答案中，如果先选框，后选枚举值，items中会出现两条信息的问题，将这两条信息合并为一条信息
 * @param {Array} items
 */
function mergeAnswerItems(items) {
  if (items.length === 0) return items;
  let fields = [];
  let enumLabel = '';
  for (let i = items.length - 1; i >= 0; i--) {
    if (items[i].fields.length !== 0) {
      fields.push(...items[i].fields);
    }
    if (typeof items[i].enumLabel === 'string') {
      enumLabel = items[i].enumLabel;
    }
  }
  items.length = 0;
  items.push(Object.assign({}, ...items, { fields, enumLabel }));
}

function parseBoxToV1(v2Box, schemaItem) {
  const { box_left, box_top, box_right, box_bottom } = v2Box.box;
  const page = v2Box.page;
  return {
    height: box_bottom - box_top + '',
    id: `page${page + 1}:${Date.now()}`,
    left: box_left + '',
    page: page,
    top: box_top + '',
    topleft: [box_top + '', box_left + ''],
    type: schemaItem.label,
    width: box_right - box_left + '',
  };
}

exports.parseAnswerToV2 = parseAnswerToV2
