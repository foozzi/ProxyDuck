import pycurl
from io import BytesIO
import re
import random
import threading
import queue


class CheckProccess(threading.Thread):
    def __init__(
        self,
        timeout=10,
        queue=None,
        result_queue=None,
        check_country=True,
        check_address=True,
    ):
        threading.Thread.__init__(self)
        self.queue = queue
        self.result_queue = result_queue
        self.timeout = timeout
        self.get_ip_url = "http://ifconfig.me/ip"
        self.ip = self.get_ip()
        self.check_country = check_country
        self.check_address = check_address

    def run(self):
        """Запуск потока"""
        while True:
            proxy = self.queue.get()

            # if isset login:password
            proxy_parts = proxy.split(":")
            if len(proxy_parts) == 4:
                user = proxy_parts[2]
                password = proxy_parts[3]
                proxy = "{}:{}".format(proxy_parts[0], proxy_parts[1])
            else:
                user = False
                password = False

            self.check_proxy(proxy, user=user, password=password)

            self.queue.task_done()

    def get_ip(self):
        r = self.send_query(url=self.get_ip_url)

        if not r:
            return ""

        return r["response"]

    def send_query(self, proxy=False, url=None, user=None, password=None):
        response = BytesIO()
        c = pycurl.Curl()

        c.setopt(c.URL, url or self.get_ip_url)
        c.setopt(c.WRITEDATA, response)
        c.setopt(c.TIMEOUT, self.timeout)

        if user is not None and password is not None:
            c.setopt(c.PROXYUSERPWD, f"{user}:{password}")

        c.setopt(c.SSL_VERIFYHOST, 0)
        c.setopt(c.SSL_VERIFYPEER, 0)

        if proxy:
            c.setopt(c.PROXY, proxy)

        # Perform request
        try:
            c.perform()
        except Exception as e:
            # print(e)
            return False

        # Return False if the status is not 200
        if c.getinfo(c.HTTP_CODE) != 200:
            return False

        # Calculate the request timeout in milliseconds
        timeout = round(c.getinfo(c.CONNECT_TIME) * 1000)

        # Decode the response content
        response = response.getvalue().decode("utf-8")

        return {"timeout": timeout, "response": response}

    def parse_anonymity(self, r):
        if self.ip in r:
            return "Transparent"

        privacy_headers = [
            "VIA",
            "X-FORWARDED-FOR",
            "X-FORWARDED",
            "FORWARDED-FOR",
            "FORWARDED-FOR-IP",
            "FORWARDED",
            "CLIENT-IP",
            "PROXY-CONNECTION",
            "X-REAL-IP",
            "X-PROXY-ID",
            "HTTP-FORWARDED",
            "FORWARDED_FOR",
            "X_FORWARDED FORWARDED",
            "CLIENT_IP",
            "PROXY-CONNECTION",
            "XROXY-CONNECTION",
            "X-IMForwards",
        ]

        if any([header in r for header in privacy_headers]):
            return "Anonymous"

        return "Elite"

    def get_country(self, ip):
        r = self.send_query(url="https://ip2c.org/" + ip)

        if r and r["response"][0] == "1":
            r = r["response"].split(";")
            return [r[3], r[1]]

        return ["-", "-"]

    def check_proxy(self, proxy, user=None, password=None):
        protocols = {}
        timeout = 0

        # Test the proxy for each protocol
        for protocol in ["http", "socks4", "socks5"]:
            r = self.send_query(
                proxy=protocol + "://" + proxy, user=user, password=password
            )
            # Check if the request failed
            if not r:
                continue

            protocols[protocol] = r
            timeout += r["timeout"]

        # Check if the proxy failed all tests
        if len(protocols) == 0:
            return
        r = protocols[random.choice(list(protocols.keys()))]["response"]

        # Get country
        if self.check_country:
            country = self.get_country(proxy.split(":")[0])

        # Check anonymity
        anonymity = self.parse_anonymity(r)

        # Check timeout
        timeout = timeout // len(protocols)

        # Check remote address
        if self.check_address:
            remote_regex = r"REMOTE_ADDR = (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
            remote_addr = re.search(remote_regex, r)
            if remote_addr:
                remote_addr = remote_addr.group(1)

        results = {
            "protocols": list(protocols.keys()),
            "anonymity": anonymity,
            "timeout": timeout,
            "address": proxy,
        }

        if self.check_country:
            results["country"] = country[0]
            results["country_code"] = country[1]

        if self.check_address:
            results["remote_address"] = remote_addr

        self.result_queue.put(results)


class RPrint(threading.Thread):
    def __init__(self, result_queue, output, is_json=False):
        threading.Thread.__init__(self)
        self.result_queue = result_queue
        self.shutdown = False
        self.output = output
        self.is_json = is_json

    def run(self):
        while not self.shutdown:
            result = self.result_queue.get()
            print(result)
            """ write data in output file """
            with open(self.output, "a") as output_file:
                if self.is_json:
                    output_file.write("{}\n".format(result))
                else:
                    output_file.write("{}\n".format(result["address"]))
            self.result_queue.task_done()

    def terminate(self):
        self.shutdown = True


class ProxyDuck:
    def __init__(
        self,
        input_filepath=None,
        output_filepath=None,
        threads=200,
        timeout=15,
        check_address=True,
        check_country=True,
        json_file_output=False,
    ):
        self.proxy_list = queue.Queue()
        self.result_queue = queue.Queue()
        self.input_filepath = input_filepath
        self.output_filepath = output_filepath
        self.threads = threads
        self.check_address = check_address
        self.check_country = check_country
        self.json_file_output = json_file_output
        self.timout = timeout

    def start(self):
        with open(self.input_filepath) as proxy_file:
            proxy_arr = proxy_file.readlines()

        for proxy in proxy_arr:
            self.proxy_list.put(proxy.strip())

        if len(proxy_arr) < self.threads:
            self.threads = len(proxy_arr)

        for _ in range(self.threads):
            proccess_worker = CheckProccess(
                self.timout,
                self.proxy_list,
                self.result_queue,
                self.check_address,
                self.check_country,
            )
            proccess_worker.daemon = True
            proccess_worker.start()

        """ Set thread for printing results """
        rprint = RPrint(self.result_queue, self.output_filepath, self.json_file_output)
        rprint.daemon = True
        rprint.start()
        self.proxy_list.join()
        rprint.terminate()
