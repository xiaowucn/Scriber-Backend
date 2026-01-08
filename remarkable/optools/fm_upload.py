#!/usr/bin/env python3
"""上传文件到临时服务器&获取公网下载链接（支持断点上传）
via: https://gitpd.paodingai.com/zhangjianfei/daily-script/-/blob/master/fm_uploader.py
Usage: python3 fm_upload.py <file_path>
"""

import base64
import hashlib
import http.client
import json
import os
import sys
from dataclasses import dataclass
from functools import cached_property
from typing import Any
from urllib.parse import quote

CHUNK_SIZE = 10 * 1024 * 1024


@dataclass
class Response:
    status: int
    content: str
    headers: http.client.HTTPMessage | dict[str, Any]

    def __post_init__(self):
        self.headers = {k.lower(): v for k, v in self.headers.items()}


class FileBrowserClient:
    headers = {
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) Jura (From P.A.I; Partner)",
        "cache-control": "no-cache",
    }
    expires = 8 * 60 * 60  # 8hours
    unit = "seconds"

    def __init__(self, host: str = "", username: str = "", password: str = "", use_https: bool = True):
        self.host = host or os.getenv("FM_HOST") or "fm.paodingai.com"
        self.username = username or os.getenv("FM_USERNAME") or "uploader"
        self.password = password or os.getenv("FM_PASSWORD") or "helloworldhowareu"
        self.use_https = use_https

    @cached_property
    def conn(self):
        http_proxy = os.getenv("http_proxy") or os.getenv("HTTP_PROXY") or None
        if http_proxy:
            import re

            rst = re.match(r"^http://([\w|.]*)(?::(\d*))?/?$", http_proxy)
            proxy_host = rst.groups()[0]
            proxy_port = rst.groups()[1] or 80
            conn = http.client.HTTPSConnection(proxy_host, proxy_port)
            conn.set_tunnel(self.host)
        else:
            if self.use_https:
                conn = http.client.HTTPSConnection(self.host)
            else:
                conn = http.client.HTTPConnection(self.host)
        return conn

    def _get_auth(self):
        payload = {
            "username": self.username,
            "password": self.password,
            "recaptcha": "",
        }
        rsp = self.request(
            "POST",
            "/api/login",
            json.dumps(payload),
            {**self.headers, "Content-Type": "application/json"},
        )
        self.headers["x-auth"] = rsp.content

    def request(self, method: str, path: str, body=None, headers=None) -> Response:
        self.conn.request(method, path, body, headers or self.headers)
        rsp = self.conn.getresponse()
        return Response(rsp.status, rsp.read().decode("utf-8"), rsp.headers)

    def request_streaming(self, method: str, path: str, body=None, headers=None):
        """Make a streaming request that returns the raw response object"""
        self.conn.request(method, path, body, headers or self.headers)
        return self.conn.getresponse()

    def set_headers(self, headers):
        self.headers.update(headers)

    def upload_and_share(self, *args, **kwargs) -> str:
        kwargs["client"] = self
        try:
            self._get_auth()
            try:
                uploader = Uploader(*args, **kwargs)
                uploader.upload()
                return self.share(os.path.basename(uploader.file_path))
            except AssertionError as e:
                if "All upload endpoints failed" in str(e):
                    print("TUS protocol upload failed, falling back to standard upload...")
                    # Fallback to standard upload would go here if implemented
                    raise e
                else:
                    raise e
        finally:
            self.conn.close()

    def download_file_streaming(self, filename: str, local_path: str, chunk_size: int = 8192) -> str:
        """Download file with streaming and resume support"""

        # Try different possible download endpoints
        endpoints = [
            f"/api/raw/{quote(filename)}",
            f"/api/resources/{quote(filename)}",
            f"/files/{quote(filename)}",
            f"/{quote(filename)}",
        ]

        # Determine download path
        if local_path.endswith(filename):
            download_path = local_path + ".server"
        else:
            download_path = os.path.join(os.path.dirname(local_path), filename + ".server")

        # Check if partial download exists
        resume_pos = 0
        if os.path.exists(download_path):
            resume_pos = os.path.getsize(download_path)

        for endpoint in endpoints:
            try:
                # Add Range header for resume support
                headers = self.headers.copy()
                if resume_pos > 0:
                    headers["Range"] = f"bytes={resume_pos}-"

                rsp = self.request_streaming("GET", endpoint, headers=headers)

                if rsp.status == http.HTTPStatus.OK or rsp.status == http.HTTPStatus.PARTIAL_CONTENT:
                    # Get total file size
                    content_length = rsp.getheader("content-length")
                    if content_length:
                        total_size = int(content_length)
                        if rsp.status == http.HTTPStatus.PARTIAL_CONTENT:
                            # For partial content, add resume position
                            content_range = rsp.getheader("content-range", "")
                            if "/" in content_range:
                                total_size = int(content_range.split("/")[-1])
                    else:
                        total_size = None

                    # Stream download to file
                    mode = "ab" if resume_pos > 0 else "wb"
                    with open(download_path, mode) as f:
                        downloaded = resume_pos

                        # Stream download in chunks
                        while True:
                            chunk = rsp.read(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)

                            if total_size:
                                progress = (downloaded / total_size) * 100
                                print(
                                    f"\rDownloading {filename}: {progress:.1f}% ({downloaded:,}/{total_size:,} bytes)",
                                    end="",
                                    flush=True,
                                )

                    if total_size:
                        print()  # New line after progress

                    return download_path

                elif rsp.status == 404:
                    continue  # Try next endpoint
                else:
                    raise Exception(f"Download failed with status: {rsp.status}")

            except Exception as e:
                if "404" in str(e):
                    continue
                # Clean up partial download on error
                if os.path.exists(download_path) and resume_pos == 0:
                    os.remove(download_path)
                raise Exception(f"Failed to download file {filename}: {e}") from e

        raise Exception(f"File {filename} not found on server (tried all endpoints)")

    def compare_files_streaming(self, local_path: str, server_filename: str, chunk_size: int = 8192) -> dict:
        """Compare local file with server file using streaming for memory efficiency"""
        import hashlib

        try:
            # Get local file info and hash
            local_size = os.path.getsize(local_path)
            local_hash = hashlib.sha256()

            print("Calculating local file hash...")
            with open(local_path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    local_hash.update(chunk)

            local_hash_hex = local_hash.hexdigest()

            # Download server file
            print("Downloading server file for comparison...")
            server_path = self.download_file_streaming(server_filename, local_path, chunk_size)

            # Get server file info and hash
            server_size = os.path.getsize(server_path)
            server_hash = hashlib.sha256()

            print("Calculating server file hash...")
            with open(server_path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    server_hash.update(chunk)

            server_hash_hex = server_hash.hexdigest()

            # Compare
            is_identical = local_hash_hex == server_hash_hex

            result = {
                "identical": is_identical,
                "local_size": local_size,
                "server_size": server_size,
                "local_hash": local_hash_hex[:16] + "...",  # Show first 16 chars
                "server_hash": server_hash_hex[:16] + "...",
                "size_diff": local_size - server_size,
                "server_file_path": server_path,
            }

            # If files are different, keep the server file for reference
            if not is_identical:
                print(f"Server file saved to: {server_path}")
            else:
                # If identical, clean up the downloaded file
                import contextlib

                with contextlib.suppress(Exception):
                    os.remove(server_path)

            return result

        except Exception as e:
            return {"error": str(e), "identical": False}

    def share(self, filename: str) -> str:
        rsp = self.request(
            "POST",
            f"/api/share/{quote(filename)}",
            json.dumps({"password": "", "expires": str(self.expires), "unit": self.unit}),
            {**self.headers, "Content-Type": "text/plain; charset=UTF-8"},
        )
        assert rsp.status == http.HTTPStatus.OK and rsp.headers.get("content-type").startswith("application/json")
        ret = json.loads(rsp.content)
        if hash_value := ret.get("hash"):
            protocol = "https" if self.use_https else "http"
            # Include filename in URL path to preserve original filename when downloading
            shared_url = f"{protocol}://{self.host}/api/public/dl/{hash_value}/{quote(filename)}"
            print(f"NOTE: Your file will be permanently deleted after {self.expires} seconds")
            print(f"FILE: {filename}")
            print(f"URL:  {shared_url}")
            return shared_url


class Uploader:
    DEFAULT_HEADERS = {"Tus-Resumable": "1.0.0"}
    CHECKSUM_ALGORITHM_PAIR = ("sha1", hashlib.sha1)

    def __init__(
        self,
        file_path: str,
        client: FileBrowserClient,
        chunk_size: int = CHUNK_SIZE,
        upload_checksum=False,
        print_progress=True,
        silent_override=False,
    ):
        self.file_path = file_path
        self.stop_at = self.get_file_size()
        self.client = client
        self.offset = 0
        self.url = None
        self.print_progress = print_progress
        self.silent_override = silent_override
        self._file_exists = False
        self.skip_upload = False  # Flag to skip upload when file is identical
        self.__init_url_and_offset()
        self.chunk_size = chunk_size
        self.request = None
        self._retried = 0
        self.upload_checksum = upload_checksum
        (
            self.__checksum_algorithm_name,
            self.__checksum_algorithm,
        ) = self.CHECKSUM_ALGORITHM_PAIR

    def get_headers(self):
        return dict(self.DEFAULT_HEADERS, **getattr(self.client, "headers", {}))

    @property
    def checksum_algorithm(self):
        """The checksum algorithm to be used for the Upload-Checksum extension."""
        return self.__checksum_algorithm

    @property
    def checksum_algorithm_name(self):
        """The name of the checksum algorithm to be used for the Upload-Checksum
        extension.
        """
        return self.__checksum_algorithm_name

    def get_offset(self):
        """
        Return offset from filebrowser server.

        This is different from the instance attribute 'offset' because this makes an
        http request to the filebrowser server to retrieve the offset.
        """
        try:
            rsp = self.client.request(
                "HEAD",
                self.url,
                body=None,
                headers=self.get_headers(),
            )
            if rsp.status == 404:
                return 0
            return int(rsp.headers.get("upload-offset") or 0)
        except Exception:
            return 0

    def __init_url_and_offset(self, url: str = None):
        filename = quote(os.path.basename(self.file_path))

        # Try different TUS endpoints
        tus_endpoints = [
            f"/api/tus/{filename}",
            f"/api/upload/tus/{filename}",
            f"/tus/{filename}",
            f"/upload/tus/{filename}",
            f"/api/files/tus/{filename}",
        ]

        if url:
            # If URL is provided, use it directly
            self.url = url
            tus_endpoints = [url]

        success = False
        for endpoint in tus_endpoints:
            self.url = endpoint
            try:
                # Add TUS-specific headers
                headers = self.get_headers()
                headers.update(
                    {
                        "Upload-Length": str(self.stop_at),
                        "Upload-Metadata": f"filename {base64.b64encode(os.path.basename(self.file_path).encode()).decode()}",
                    }
                )

                rsp = self.client.request(
                    "POST",
                    self.url,
                    body=None,
                    headers=headers,
                )

                # Handle different HTTP status codes
                if rsp.status == http.HTTPStatus.CREATED:
                    # File created successfully, continue normally
                    success = True
                    # Extract upload URL from Location header if available
                    if "location" in rsp.headers:
                        location_url = rsp.headers["location"]
                        # Handle relative URLs
                        if location_url.startswith("/"):
                            self.url = location_url
                        else:
                            # If it's a full URL, extract the path
                            from urllib.parse import urlparse

                            parsed = urlparse(location_url)
                            self.url = parsed.path
                    break
                elif rsp.status == http.HTTPStatus.OK:
                    # File already exists, this is also acceptable for TUS protocol
                    success = True
                    break
                elif rsp.status == http.HTTPStatus.CONFLICT:
                    # 409 Conflict indicates file exists - handle based on mode
                    if self.silent_override:
                        # In silent mode, automatically override
                        override_endpoint = endpoint + "?override=true"
                        try:
                            headers = self.get_headers()
                            headers.update(
                                {
                                    "Upload-Length": str(self.stop_at),
                                    "Upload-Metadata": f"filename {base64.b64encode(os.path.basename(self.file_path).encode()).decode()}",
                                }
                            )

                            override_rsp = self.client.request(
                                "POST",
                                override_endpoint,
                                body=None,
                                headers=headers,
                            )

                            if override_rsp.status in [200, 201]:
                                success = True
                                self.url = override_endpoint
                                # Extract upload URL from Location header if available
                                if "location" in override_rsp.headers:
                                    location_url = override_rsp.headers["location"]
                                    if location_url.startswith("/"):
                                        self.url = location_url
                                    else:
                                        from urllib.parse import urlparse

                                        parsed = urlparse(location_url)
                                        self.url = parsed.path
                                break
                        except Exception:
                            continue
                    else:
                        # In interactive mode, mark as existing file for later handling
                        success = True
                        self._file_exists = True
                        break
                else:
                    continue

            except Exception as e:
                print(f"Error trying endpoint {endpoint}: {e}")
                continue

        if not success:
            # If all TUS endpoints fail, try to create upload via resources API
            try:
                self.url = f"/api/resources/{filename}"
                headers = self.get_headers()
                headers.update({"Upload-Length": str(self.stop_at), "Content-Type": "application/offset+octet-stream"})

                rsp = self.client.request("POST", self.url, body=None, headers=headers)
                if rsp.status in [200, 201]:
                    success = True
            except Exception:
                pass

        if not success:
            raise AssertionError("All upload endpoints failed. Server may not support TUS protocol or API has changed.")

        self.offset = self.get_offset()

        # Check if file exists (either from offset or conflict detection)
        file_exists = self.offset > 0 or self._file_exists

        if file_exists:
            if self.silent_override:
                self.__init_url_and_offset(self.url + "?override=true")
                return

            filename = os.path.basename(self.file_path)
            if self.offset > 0:
                print(f"The file has been uploaded {self.offset} bytes")
                print("Maybe it's already uploaded by another people")
            else:
                print(f"File '{filename}' already exists on server")

            # Offer to compare files
            compare_choice = input("Do you want to compare with server file? [y/N]: ")
            if compare_choice.strip().lower() == "y":
                print("Starting file comparison (this may take a while for large files)...")
                try:
                    comparison = self.client.compare_files_streaming(self.file_path, filename)
                    if "error" in comparison:
                        print(f"Comparison failed: {comparison['error']}")
                    else:
                        print("\n=== File Comparison ===")
                        print(f"Files identical: {'Yes' if comparison['identical'] else 'No'}")
                        print(f"Local file size:  {comparison['local_size']:,} bytes")
                        print(f"Server file size: {comparison['server_size']:,} bytes")
                        if comparison["size_diff"] != 0:
                            print(f"Size difference:  {comparison['size_diff']:+,} bytes")
                        print(f"Local hash:  {comparison['local_hash']}")
                        print(f"Server hash: {comparison['server_hash']}")
                        if not comparison["identical"] and "server_file_path" in comparison:
                            print(f"Server file saved: {comparison['server_file_path']}")
                        print("========================\n")

                        if comparison["identical"]:
                            print("Files are identical. No need to upload.")
                            skip_upload = input("Skip upload and get share link directly? [Y/n]: ")
                            if skip_upload.strip().lower() != "n":
                                print("Upload skipped. Will get share link for existing file.")
                                self.skip_upload = True
                                return
                        else:
                            print("Files are different.")
                            if "server_file_path" in comparison:
                                print(f"You can review the server file at: {comparison['server_file_path']}")
                except Exception as e:
                    print(f"Comparison failed: {e}")

            continue_upload = input("Do you want to continue upload? [y/N]: ")
            if continue_upload.strip().lower() != "y":
                sys.exit(0)

            if self.offset > 0:
                # Partial upload exists, offer resume or overwrite
                override_or_resume = input("Overwrite or Resume? [o/R]: ")
                if override_or_resume.strip().lower() == "o":
                    # Re-initialize with override parameter
                    override_url = self.url + "?override=true"
                    self._reinit_with_override(override_url)
            else:
                # Complete file exists, only offer overwrite
                print("File will be overwritten.")
                # Re-initialize with override parameter
                override_url = self.url + "?override=true"
                self._reinit_with_override(override_url)

    def _reinit_with_override(self, override_url: str):
        """Re-initialize upload with override parameter, bypassing interactive prompts"""
        try:
            headers = self.get_headers()
            headers.update(
                {
                    "Upload-Length": str(self.stop_at),
                    "Upload-Metadata": f"filename {base64.b64encode(os.path.basename(self.file_path).encode()).decode()}",
                }
            )

            rsp = self.client.request("POST", override_url, body=None, headers=headers)

            if rsp.status in [200, 201]:
                self.url = override_url
                # Extract upload URL from Location header if available
                if "location" in rsp.headers:
                    location_url = rsp.headers["location"]
                    if location_url.startswith("/"):
                        self.url = location_url
                    else:
                        from urllib.parse import urlparse

                        parsed = urlparse(location_url)
                        self.url = parsed.path
                # Reset offset for fresh upload
                self.offset = 0
                self._file_exists = False
            else:
                raise Exception(f"Override failed with status: {rsp.status}")
        except Exception as e:
            raise Exception(f"Failed to override file: {e}") from e

    def get_request_length(self):
        remainder = self.stop_at - self.offset
        return self.chunk_size if remainder > self.chunk_size else remainder

    def get_file_stream(self):
        if not os.path.isfile(self.file_path):
            raise ValueError("invalid file {}".format(self.file_path))
        return open(self.file_path, "rb")

    def get_file_size(self):
        return os.path.getsize(self.file_path)

    def upload(self):
        # Check if upload should be skipped (file is identical)
        if self.skip_upload:
            if self.print_progress:
                print("Skipping upload for identical file.")
            return

        try:
            while self.offset < self.stop_at:
                self.upload_chunk()
                if self.print_progress:
                    print(
                        f"Total: {self.stop_at} bytes, Uploaded: {self.offset} bytes, Remain: "
                        f"{(self.stop_at - self.offset) / self.stop_at * 100:.2f}%",
                        end="\r",
                    )
        finally:
            if self.request and (file := self.request.file):
                file.close()
            if self.print_progress:
                print("", end="\r")

    def upload_chunk(self):
        self._retried = 0
        if rsp := self._do_request():
            self.offset = int(rsp.headers.get("upload-offset"))

    def _do_request(self):
        self.request = TusRequest(self)
        return self.request.perform()


class TusRequest:
    def __init__(self, uploader: Uploader):
        self._client = uploader.client
        self._url = uploader.url
        self.file = uploader.get_file_stream()
        self.file.seek(uploader.offset)

        self._request_headers = {
            "upload-offset": str(uploader.offset),
            "Content-Type": "application/offset+octet-stream",
        }
        self._request_headers.update(uploader.get_headers())
        self._content_length = uploader.get_request_length()
        self._upload_checksum = uploader.upload_checksum
        self._checksum_algorithm = uploader.checksum_algorithm
        self._checksum_algorithm_name = uploader.checksum_algorithm_name

    def add_checksum(self, chunk: bytes):
        if self._upload_checksum:
            self._request_headers["upload-checksum"] = " ".join(
                (
                    self._checksum_algorithm_name,
                    base64.b64encode(self._checksum_algorithm(chunk).digest()).decode("ascii"),
                )
            )

    def perform(self):
        chunk = self.file.read(self._content_length)
        self.add_checksum(chunk)
        rsp = self._client.request(
            "PATCH",
            self._url,
            chunk,
            self._request_headers,
        )
        if rsp.status < http.HTTPStatus.OK or rsp.status > http.HTTPStatus.MULTIPLE_CHOICES:
            raise http.client.HTTPException(f"Upload failed with status: {rsp.status}")
        return rsp


class FMUploader:
    """Just for backward compatibility"""

    def upload(self, path, use_https=True):
        from pathlib import Path

        if isinstance(path, str):
            path = Path(path)
        assert isinstance(path, Path), "path must be a string or a pathlib.Path object"
        return FileBrowserClient(use_https=use_https).upload_and_share(
            path.as_posix(), chunk_size=CHUNK_SIZE, print_progress=False, silent_override=True
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Upload file to filebrowser server")
    parser.add_argument("file", help="file path to upload")
    parser.add_argument("--host", help='filebrowser server host, default to "fm.paodingai.com"', default="")
    parser.add_argument("--username", help="filebrowser server username, default to 'xxx'", default="")
    parser.add_argument(
        "--password",
        help="filebrowser server password, default to '***'",
        default="",
    )
    parser.add_argument(
        "--chunk-size",
        help="chunk size in bytes, default to 10MB",
        type=int,
        default=CHUNK_SIZE,
    )
    parser.add_argument(
        "--upload-checksum",
        help="whether or not to supply the Upload-Checksum header along with each chunk",
        type=lambda x: x.lower() in ("true", "1", "yes", "t"),
        default=False,
    )
    parser.add_argument(
        "--print-progress",
        help="whether or not to supply the Upload-Checksum header along with each chunk",
        type=lambda x: x.lower() in ("true", "1", "yes", "t"),
        default=True,
    )
    parser.add_argument(
        "--silent-override",
        help="whether or not to override the existing file without asking",
        type=lambda x: x.lower() in ("true", "1", "yes", "t"),
        default=False,
    )
    parser.add_argument(
        "--use-https",
        help="whether to use HTTPS connection (default: True)",
        type=lambda x: x.lower() in ("true", "1", "yes", "t"),
        default=True,
    )
    args = parser.parse_args()
    client = FileBrowserClient(args.host, args.username, args.password, args.use_https)
    client.upload_and_share(
        args.file,
        chunk_size=args.chunk_size,
        upload_checksum=args.upload_checksum,
        print_progress=args.print_progress,
        silent_override=args.silent_override,
    )
