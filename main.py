import traceback

from flask import Flask, jsonify, request, render_template, session, send_file
from flask_cors import CORS, cross_origin

from models import db, Contact
from config import Config
from io import BytesIO
import pandas as pd

app = Flask(__name__)
app.config.from_object(Config)
cors = CORS()
db.init_app(app)

with app.app_context():
    db.create_all()


# 登录功能
@app.route('/login', methods=['POST'])
@cross_origin()
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if username == 'admin' and password == '123456':
        session['logged_in'] = True  # 设置 session 标记用户已登录
        return jsonify({'message': 'Login successful'})
    return jsonify({'message': 'Invalid username or password'}), 401


# 注销功能
@app.route('/logout', methods=['POST'])
@cross_origin()
def logout():
    session.pop('logged_in', None)
    return jsonify({'message': 'Logged out successfully'})


# 增加联系人
@app.route('/contacts/add', methods=['POST'])
@cross_origin()
def add_contact():
    data = request.json
    new_contact = Contact(name=data['name'], phone=data['phone'], email=data.get('email'), qq=data.get('qq'),
                          wechat=data.get('wechat'), address=data.get("address"))
    db.session.add(new_contact)
    db.session.commit()
    return jsonify({'message': 'Contact added successfully'})


# 查询联系人
@app.route('/contacts/list', methods=['GET'])
@cross_origin()
def get_contacts():
    contacts = Contact.query.all()
    return jsonify(
        [{'id': c.id, 'name': c.name, 'phone': c.phone, 'qq': c.qq, 'wechat': c.wechat, 'email': c.email,
          "address": c.address, 'stock': c.stock} for c in contacts])


# 联系人信息
@app.route('/contacts/info/<int:id>', methods=['GET'])
@cross_origin()
def contacts_info(id):
    c = Contact.query.filter_by(id=id).first()
    return jsonify({'id': c.id, 'name': c.name, 'phone': c.phone, 'qq': c.qq, 'wechat': c.wechat, 'email': c.email,
                    "address": c.address, "stock": c.stock})


# 更新联系人
@app.route('/contacts/edit/<int:id>', methods=["POST"])
@cross_origin()
def update_contact(id):
    data = request.json
    contact = Contact.query.get(id)
    if contact:
        contact.name = data['name']
        contact.phone = data['phone']
        contact.email = data.get('email')
        contact.address = data.get('address')
        contact.qq = data.get('qq')
        contact.wechat = data.get('wechat')
        db.session.commit()
        return jsonify({'message': 'Contact updated successfully'})
    return jsonify({'message': 'Contact not found'}), 404

@app.route('/contacts/favorites', methods=['GET'])
@cross_origin()
def get_favorites():
    # 查询数据库中 stack 为 1 的联系人（已收藏）
    favorites = Contact.query.filter_by(stock=1).all()

    # 将收藏联系人信息转换为字典列表
    favorite_data = [
        {
            'name': c.name,
            'phone': c.phone,
            'qq': c.qq,
            'wechat': c.wechat,
            'email': c.email,
            'address': c.address
        }
        for c in favorites
    ]
    return jsonify(favorite_data)



# 删除联系人
@app.route('/contacts/delete/<int:id>', methods=['DELETE'])
@cross_origin()
def delete_contact(id):
    contact = Contact.query.get(id)
    if contact:
        db.session.delete(contact)
        db.session.commit()
        return jsonify({'message': 'Contact deleted successfully'})
    return jsonify({'message': 'Contact not found'}), 404


# 批量删除联系人
@app.route('/contacts/deleteBatch', methods=['DELETE'])
@cross_origin()
def delete_contacts():
    ids = request.json.get('ids', [])
    if ids:
        Contact.query.filter(Contact.id.in_(ids)).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({'message': '联系人删除成功!'}), 200
    return jsonify({'message': 'No IDs provided!'}), 400


@app.route('/contacts/export/excel', methods=['GET'])
@cross_origin()
def export_to_excel():
    ids = request.args.getlist('ids', type=int)

    if not ids:
        return jsonify({'message': '没有选中的数据！'}), 400

    # 查询选中的联系人
    contacts = Contact.query.filter(Contact.id.in_(ids)).all()

    # 将联系人数据转换为 DataFrame
    data = [{'id': c.id, '姓名': c.name, '电话':
        c.phone, 'QQ': c.qq, "微信": c.wechat, "邮箱": c.email, "地址": c.address,
             "收否收藏": '是' if c.stock == 1 else '否'} for c in contacts]
    df = pd.DataFrame(data)

    # 使用 pandas 保存为 Excel 格式
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Contacts')

    output.seek(0)  # 重置文件指针

    # 返回文件作为响应
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='contacts.xlsx'
    )



@app.route('/contacts/template', methods=['GET'])
@cross_origin()
def download_template():
    # 创建空的 DataFrame，仅包含表头
    data = [{'姓名': '', '电话': '', 'QQ': '', "微信": '', "邮箱": '', "地址": ''}]
    df = pd.DataFrame(data)

    # 使用 pandas 保存为 Excel 格式
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Contacts Template')

    output.seek(0)  # 重置文件指针

    # 返回文件作为响应
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='template.xlsx'
    )


@app.route('/contacts/import/excel', methods=['POST'])
@cross_origin()
def import_from_excel():
    file = request.files.get('file')
    if not file or not file.filename.endswith('.xlsx'):
        return jsonify({'message': '请上传 Excel 文件！'}), 400

    # 读取 Excel 文件
    try:
        df = pd.read_excel(file, engine='openpyxl')
        for _, row in df.iterrows():
            name = row.get('姓名')
            phone = row.get('电话')
            qq = row.get('QQ')
            wechat = row.get('微信')
            email = row.get('邮箱')
            address = row.get('地址')

            if pd.notna(name) and pd.notna(phone):  # 确保数据有效
                new_contact = Contact(name=name, phone=str(phone), qq=qq, wechat=wechat, email=email, address=address)
                db.session.add(new_contact)
        db.session.commit()
        return jsonify({'message': '导入成功！'}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'message': f'导入失败: {str(e)}'}), 500


@app.route('/contacts/toggle_stack/<int:id>', methods=['POST'])
@cross_origin()
def toggle_stack(id):
    contact = Contact.query.get_or_404(id)

    # 切换收藏状态
    contact.stock = 1 if contact.stock == 0 else 0

    db.session.commit()

    return jsonify({'message': '收藏状态更新成功', 'stack': contact.stock})


if __name__ == '__main__':
    app.run(debug=True, port=8888, host="0.0.0.0")
