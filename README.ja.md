<h1 align="center">📋 勤怠管理システム</h1>

<h2 align="center"><a href="README.md">中文</a> ｜ 日本語 ｜ <a href="README.en.md">English</a></h2>

## 現在のバージョンと機能

公開済みのダウンロード版は **v1.0.2** です。個人コードによるシフト希望、QRコード打刻、アクセス制御の更新を含みます。ソースからの起動には Python が必要です。配布済みの実行ファイルには不要です。

- 従業員管理、曜日別の勤務時間、希望提出、自動シフト作成、打刻修正、集計のエクスポート。
- 原版を含む **11 種類の打刻画面**。すべてに成功アニメーションがあり、SF と着物の画面は Three.js を使用します。
- 管理画面でプレビュー、適用、前のスタイルへの復元が可能。従業員の打刻 URL は変わりません。
- スタイル管理は中国語・英語・日本語に対応し、プレビューも選択言語に従います。

## アクセス先

起動中に、アプリを実行しているパソコンで開いてください。

| 画面 | アドレス |
| --- | --- |
| 打刻 | http://127.0.0.1:5000/ |
| 管理 | http://127.0.0.1:5000/admin/ |
| 画面スタイル（最新ソース） | http://127.0.0.1:5000/admin/appearance |

`5077` は初期デモ用です。通常の起動では `5000` を使用します。「管理」リンクがない場合は上記の管理 URL を直接開いてください。手元で作成済みのデスクトップショートカットも利用できますが、リポジトリが自動作成するものではありません。

スタイル管理は実行元のパソコンでのみ可能です。完全な管理者ログイン・権限機能は未実装のため、信頼できるネットワークで使用してください。操作、スマートフォン、バックアップは [使用説明](USER_GUIDE.ja.md) を参照してください。

<h1>ダウンロード</h1>

<h2>🪟 <a href="https://github.com/20220402jp-coder/attendance-management-system/releases/download/v1.0.2/AttendanceSystem-1.0.2-Windows-x64.exe.zip">Windowsはこちらからダウンロード</a></h2>

<h2>🍎 <a href="https://github.com/20220402jp-coder/attendance-management-system/releases/download/v1.0.2/AttendanceSystem-1.0.2-macOS-arm64.zip">Macはこちらからダウンロード（M1、M2、M3、M4）</a></h2>

<h2>🍎 <a href="https://github.com/20220402jp-coder/attendance-management-system/releases/download/v1.0.2/AttendanceSystem-1.0.2-macOS-x64.zip">Intel搭載Macはこちらからダウンロード</a></h2>

<h2>🐧 <a href="https://github.com/20220402jp-coder/attendance-management-system/releases/download/v1.0.2/AttendanceSystem-1.0.2-Linux-x64.zip">Linuxはこちらからダウンロード</a></h2>

シンプルな勤怠・シフト管理を必要とする小規模事業者向けのシステムです。中国語、英語、日本語に対応しています。

<h1>使い方</h1>

<h2>1. お使いのパソコンに合うファイルをダウンロードします</h2>

<h2>2. ダウンロードした圧縮ファイルを展開します</h2>

<h2>3. 中にあるプログラムをダブルクリックします</h2>

起動すると、自動的にブラウザが開きます。初めて使うときは「管理 → 従業員管理」を開き、従業員を登録してください。終了するときは、プログラムのウィンドウを閉じてください。

### Windowsで安全に関する警告が表示された場合

「詳細情報」をクリックし、「実行」をクリックしてください。

### Macで開けない場合

プログラムを右クリックして「開く」を選びます。それでも開けない場合は、「システム設定 → プライバシーとセキュリティ」を開き、「このまま開く」をクリックしてください。

### Linuxでダブルクリックしても起動しない場合

```bash
chmod +x AttendanceSystem-*-Linux-*
```

Pythonなど、ほかのソフトをインストールする必要はありません。

<h2>📖 <a href="USER_GUIDE.ja.md">詳しい使用説明を開く</a></h2>
