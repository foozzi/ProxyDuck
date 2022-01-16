from proxyduck import ProxyDuck
import argparse


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ProxyDuck 🦆 - Very simple and powerful multithreading proxy checker [socks4/5, http/s]"
    )
    parser.add_argument(
        "-i", dest="input_filepath", required=True, help="Input file with proxy"
    )
    parser.add_argument(
        "-o",
        dest="output_filepath",
        required=True,
        help="Output file with checked proxies",
    )
    parser.add_argument(
        "-t",
        dest="threads",
        required=False,
        default=200,
        help="Number of threads (default: 200)",
    )
    parser.add_argument(
        "-to", dest="timeout", required=False, default=15, help="Timeout in seconds"
    )
    parser.add_argument(
        "-ca",
        dest="check_address",
        required=False,
        default=True,
        help="Check outgoing address",
    )
    parser.add_argument(
        "-cc",
        dest="check_country",
        required=False,
        default=True,
        help="Check proxy country",
    )
    parser.add_argument(
        "-jo",
        dest="json_file_output",
        required=False,
        default=False,
        help="Output in file data json",
    )

    args = parser.parse_args()

    ProxyDuck(
        args.input_filepath,
        args.output_filepath,
        args.threads,
        args.timeout,
        args.check_address,
        args.check_country,
        args.json_file_output,
    ).start()
