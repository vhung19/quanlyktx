from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)
DB_NAME = 'ktx.db'


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Giúp trả kết quả dạng dictionary giống pymysql
    return conn


# Tự động khởi tạo database và các bảng nếu chưa tồn tại khi chạy ứng dụng
def init_db():
    conn = get_db_connection()
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS Phong (
            SoPhong TEXT PRIMARY KEY,
            LoaiPhong TEXT,
            SoNguoiToiDa INTEGER NOT NULL DEFAULT 4
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS SinhVien (
            STT INTEGER PRIMARY KEY AUTOINCREMENT,
            MaSV TEXT UNIQUE NOT NULL,
            HoTen TEXT NOT NULL,
            MaLop TEXT NOT NULL,
            CCCD TEXT UNIQUE NOT NULL,
            SoPhong TEXT,
            FOREIGN KEY (SoPhong) REFERENCES Phong(SoPhong) ON DELETE SET NULL
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS DangKyDichVu (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            MaSV TEXT NOT NULL,
            TenDichVu TEXT NOT NULL,
            DonGia REAL NOT NULL,
            Thang INTEGER NOT NULL,
            Nam INTEGER NOT NULL,
            FOREIGN KEY (MaSV) REFERENCES SinhVien(MaSV) ON DELETE CASCADE
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS ChiSoDienNuoc (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            SoPhong TEXT NOT NULL,
            Thang INTEGER NOT NULL,
            Nam INTEGER NOT NULL,
            SoDienCu INTEGER NOT NULL DEFAULT 0,
            SoDienMoi INTEGER NOT NULL DEFAULT 0,
            SoNuocCu INTEGER NOT NULL DEFAULT 0,
            SoNuocMoi INTEGER NOT NULL DEFAULT 0,
            UNIQUE(SoPhong, Thang, Nam),
            FOREIGN KEY (SoPhong) REFERENCES Phong(SoPhong) ON DELETE CASCADE
        );
        """)
    conn.close()


# ==========================================
# 1. QUẢN LÝ PHÒNG (Trang chủ /)
# ==========================================
@app.route('/')
def quan_ly_phong():
    conn = get_db_connection()
    phongs = conn.execute("""
        SELECT p.SoPhong, p.LoaiPhong, COUNT(sv.MaSV) AS SoThanhVien 
        FROM Phong p 
        LEFT JOIN SinhVien sv ON p.SoPhong = sv.SoPhong 
        GROUP BY p.SoPhong, p.LoaiPhong
    """).fetchall()
    conn.close()
    return render_template('phong.html', phongs=phongs)


@app.route('/them-phong', methods=['POST'])
def them_phong():
    so_phong = request.form['SoPhong'].strip()
    loai_phong = request.form['LoaiPhong'].strip()
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO Phong (SoPhong, LoaiPhong) VALUES (?, ?)", (so_phong, loai_phong))
        conn.commit()
    except Exception as e:
        print(f"Lỗi thêm phòng: {e}")
    conn.close()
    return redirect(url_for('quan_ly_phong'))


@app.route('/xoa-phong/<so_phong>')
def xoa_phong(so_phong):
    conn = get_db_connection()
    conn.execute("DELETE FROM Phong WHERE SoPhong = ?", (so_phong,))
    conn.commit()
    conn.close()
    return redirect(url_for('quan_ly_phong'))


# ==========================================
# 2. QUẢN LÝ SINH VIÊN
# ==========================================
@app.route('/sinh-vien')
def quan_ly_sinh_vien():
    conn = get_db_connection()
    sinh_viens = conn.execute("""
        SELECT sv.*, p.LoaiPhong 
        FROM SinhVien sv 
        LEFT JOIN Phong p ON sv.SoPhong = p.SoPhong
        ORDER BY sv.STT ASC
    """).fetchall()

    phongs = conn.execute("SELECT SoPhong, LoaiPhong FROM Phong").fetchall()
    conn.close()
    return render_template('sinh_vien.html', sinh_viens=sinh_viens, phongs=phongs)


@app.route('/them-sinh-vien', methods=['POST'])
def them_sinh_vien():
    ma_sv = request.form['MaSV'].strip()
    ho_ten = request.form['HoTen'].strip()
    ma_lop = request.form['MaLop'].strip()
    cccd = request.form['CCCD'].strip()
    so_phong = request.form['SoPhong']

    conn = get_db_connection()
    if so_phong:
        count = conn.execute("SELECT COUNT(*) AS count FROM SinhVien WHERE SoPhong = ?", (so_phong,)).fetchone()[
            'count']
        if count >= 4:
            conn.close()
            return f"<script>alert('Lỗi: Phòng {so_phong} đã đạt tối đa 4 thành viên!'); window.location.href='/sinh-vien';</script>"

    try:
        conn.execute("""
            INSERT INTO SinhVien (MaSV, HoTen, MaLop, CCCD, SoPhong) 
            VALUES (?, ?, ?, ?, ?)
        """, (ma_sv, ho_ten, ma_lop, cccd, so_phong if so_phong else None))
        conn.commit()
    except Exception as e:
        print(f"Lỗi thêm sinh viên: {e}")
    conn.close()
    return redirect(url_for('quan_ly_sinh_vien'))


@app.route('/sua-sinh-vien/<ma_sv>', methods=['POST'])
def sua_sinh_vien(ma_sv):
    ho_ten = request.form['HoTen'].strip()
    ma_lop = request.form['MaLop'].strip()
    cccd = request.form['CCCD'].strip()
    so_phong = request.form['SoPhong']

    conn = get_db_connection()
    sv_hien_tai = conn.execute("SELECT SoPhong FROM SinhVien WHERE MaSV = ?", (ma_sv,)).fetchone()

    if so_phong and (not sv_hien_tai or sv_hien_tai['SoPhong'] != so_phong):
        count = conn.execute("SELECT COUNT(*) AS count FROM SinhVien WHERE SoPhong = ?", (so_phong,)).fetchone()[
            'count']
        if count >= 4:
            conn.close()
            return f"<script>alert('Lỗi: Phòng {so_phong} chuyển đến đã đạt tối đa 4 thành viên!'); window.location.href='/sinh-vien';</script>"

    conn.execute("""
        UPDATE SinhVien 
        SET HoTen=?, MaLop=?, CCCD=?, SoPhong=? 
        WHERE MaSV=?
    """, (ho_ten, ma_lop, cccd, so_phong if so_phong else None, ma_sv))
    conn.commit()
    conn.close()
    return redirect(url_for('quan_ly_sinh_vien'))


@app.route('/xoa-sinh-vien/<ma_sv>')
def xoa_sinh_vien(ma_sv):
    conn = get_db_connection()
    conn.execute("DELETE FROM SinhVien WHERE MaSV = ?", (ma_sv,))
    conn.commit()
    conn.close()
    return redirect(url_for('quan_ly_sinh_vien'))


# ==========================================
# 3. QUẢN LÝ DỊCH VỤ CÁ NHÂN
# ==========================================
@app.route('/dich-vu', methods=['GET', 'POST'])
def quan_ly_dich_vu():
    conn = get_db_connection()
    if request.method == 'POST':
        ma_sv = request.form['MaSV']
        ten_dv = request.form['TenDichVu']
        don_gia = 90000 if ten_dv == 'GuiXe' else 250000
        thang = int(request.form['Thang'])
        nam = int(request.form['Nam'])

        conn.execute("""
            INSERT INTO DangKyDichVu (MaSV, TenDichVu, DonGia, Thang, Nam) 
            VALUES (?, ?, ?, ?, ?)
        """, (ma_sv, ten_dv, don_gia, thang, nam))
        conn.commit()
        conn.close()
        return redirect(url_for('quan_ly_dich_vu'))

    dich_vus = conn.execute("""
        SELECT dv.*, sv.HoTen, sv.SoPhong 
        FROM DangKyDichVu dv
        JOIN SinhVien sv ON dv.MaSV = sv.MaSV
        ORDER BY dv.ID DESC
    """).fetchall()
    sinh_viens = conn.execute("SELECT MaSV, HoTen FROM SinhVien").fetchall()
    conn.close()
    return render_template('dich_vu.html', dich_vus=dich_vus, sinh_viens=sinh_viens)


@app.route('/sua-dich-vu/<int:dv_id>', methods=['POST'])
def sua_dich_vu(dv_id):
    ten_dv = request.form['TenDichVu']
    don_gia = 90000 if ten_dv == 'GuiXe' else 250000
    thang = int(request.form['Thang'])
    nam = int(request.form['Nam'])

    conn = get_db_connection()
    conn.execute("""
        UPDATE DangKyDichVu 
        SET TenDichVu=?, DonGia=?, Thang=?, Nam=? 
        WHERE ID=?
    """, (ten_dv, don_gia, thang, nam, dv_id))
    conn.commit()
    conn.close()
    return redirect(url_for('quan_ly_dich_vu'))


@app.route('/xoa-dich-vu/<int:dv_id>')
def xoa_dich_vu(dv_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM DangKyDichVu WHERE ID = ?", (dv_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('quan_ly_dich_vu'))


# ==========================================
# 4. HÓA ĐƠN & ĐIỆN NƯỚC
# ==========================================
@app.route('/hoa-don', methods=['GET', 'POST'])
def hoa_don():
    conn = get_db_connection()
    selected_thang = int(request.form.get('Thang', 10))
    selected_nam = int(request.form.get('Nam', 2026))

    if request.method == 'POST' and 'CapNhatChiSo' in request.form:
        so_phong = request.form['SoPhong']
        dien_cu = int(request.form['SoDienCu'])
        dien_moi = int(request.form['SoDienMoi'])
        nuoc_cu = int(request.form['SoNuocCu'])
        nuoc_moi = int(request.form['SoNuocMoi'])

        conn.execute("""
            INSERT INTO ChiSoDienNuoc (SoPhong, Thang, Nam, SoDienCu, SoDienMoi, SoNuocCu, SoNuocMoi)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(SoPhong, Thang, Nam) DO UPDATE SET 
                SoDienCu=excluded.SoDienCu, SoDienMoi=excluded.SoDienMoi,
                SoNuocCu=excluded.SoNuocCu, SoNuocMoi=excluded.SoNuocMoi
        """, (so_phong, selected_thang, selected_nam, dien_cu, dien_moi, nuoc_cu, nuoc_moi))
        conn.commit()

    phongs = conn.execute("SELECT SoPhong FROM Phong").fetchall()
    hoa_don_phongs = []

    for p in phongs:
        so_phong = p['SoPhong']
        thanh_viens = conn.execute("SELECT MaSV, HoTen FROM SinhVien WHERE SoPhong = ?", (so_phong,)).fetchall()
        so_thanh_vien = len(thanh_viens)

        if so_thanh_vien == 0:
            continue

        tien_phong = so_thanh_vien * 350000
        phi_ve_sinh = so_thanh_vien * 50000

        tien_dich_vu_ca_nhan = 0
        for tv in thanh_viens:
            res_dv = conn.execute("""
                SELECT SUM(DonGia) AS TotalDV FROM DangKyDichVu 
                WHERE MaSV = ? AND Thang = ? AND Nam = ?
            """, (tv['MaSV'], selected_thang, selected_nam)).fetchone()
            if res_dv and res_dv['TotalDV']:
                tien_dich_vu_ca_nhan += res_dv['TotalDV']

        dn = conn.execute("""
            SELECT * FROM ChiSoDienNuoc 
            WHERE SoPhong = ? AND Thang = ? AND Nam = ?
        """, (so_phong, selected_thang, selected_nam)).fetchone()

        so_dien_tieu_thu = 0
        tien_dien = 0
        so_nuoc_tieu_thu = 0
        tien_nuoc = 0

        if dn:
            so_dien_tieu_thu = max(0, dn['SoDienMoi'] - dn['SoDienCu'])
            mien_phi_dien = 10 * so_thanh_vien
            so_dien_tinh_tien = max(0, so_dien_tieu_thu - mien_phi_dien)
            tien_dien = so_dien_tinh_tien * 2500

            so_nuoc_tieu_thu = max(0, dn['SoNuocMoi'] - dn['SoNuocCu'])
            mien_phi_nuoc = 10 * so_thanh_vien
            so_nuoc_tinh_tien = max(0, so_nuoc_tieu_thu - mien_phi_nuoc)
            tien_nuoc = so_nuoc_tinh_tien * 18000

        tong_cong = tien_phong + phi_ve_sinh + tien_dich_vu_ca_nhan + tien_dien + tien_nuoc

        hoa_don_phongs.append({
            'SoPhong': so_phong,
            'SoThanhVien': so_thanh_vien,
            'ThanhViens': thanh_viens,
            'TienPhong': tien_phong,
            'PhiVeSinh': phi_ve_sinh,
            'TienDichVu': tien_dich_vu_ca_nhan,
            'SoDienTieuThu': so_dien_tieu_thu,
            'TienDien': tien_dien,
            'SoNuocTieuThu': so_nuoc_tieu_thu,
            'TienNuoc': tien_nuoc,
            'TongCong': tong_cong,
            'ChiSo': dn if dn else {'SoDienCu': 0, 'SoDienMoi': 0, 'SoNuocCu': 0, 'SoNuocMoi': 0}
        })

    conn.close()
    return render_template('hoa_don.html', hoa_don_phongs=hoa_don_phongs, thang=selected_thang, nam=selected_nam)


if __name__ == '__main__':
    init_db()  # Tự động tạo file ktx.db và các bảng khi chạy app.py
    app.run(debug=True)