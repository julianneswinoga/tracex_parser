#### [2.4.3](https://github.com/julianneswinoga/tracex_parser/compare/2.4.2...2.4.3)

> 29 September 2023

- Made snap build much smaller [`0e2282e`](https://github.com/julianneswinoga/tracex_parser/commit/0e2282e803d4af2ff849e149a357cbd497320c65)

#### [2.4.2](https://github.com/julianneswinoga/tracex_parser/compare/2.4.1...2.4.2)

> 29 September 2023

- Js/add snap build [`#1`](https://github.com/julianneswinoga/tracex_parser/pull/1)

#### [2.4.1](https://github.com/julianneswinoga/tracex_parser/compare/2.4.0...2.4.1)

> 13 September 2023

- Update CLI docs [`c0e852f`](https://github.com/julianneswinoga/tracex_parser/commit/c0e852f37036a97d7f4dd633db69d2d4a75f12c3)
- Exclude .trx demo files from package build [`bec46ce`](https://github.com/julianneswinoga/tracex_parser/commit/bec46cef5865a4ba7b929be84a507119e5038768)

#### [2.4.0](https://github.com/julianneswinoga/tracex_parser/compare/2.3.0...2.4.0)

> 12 September 2023

- Add `parse-trx` as an installed script, needed to massage `file_parser.py`'s main function to do this [`e5b10dc`](https://github.com/julianneswinoga/tracex_parser/commit/e5b10dc88e3b25a02fafda566132954caf37bfb0)
- Add the rest of the app-parsed text files, and an exception for demo_netx_udp.txt... [`a3b209e`](https://github.com/julianneswinoga/tracex_parser/commit/a3b209e101905a4b0acb5035baf83c736c9e29d8)
- Convert raw test loop into pytest parameters [`e6b1e56`](https://github.com/julianneswinoga/tracex_parser/commit/e6b1e5627a811325ea87fc4e2a2a45a0acbec2dd)
- Update README.md script output after previous changes/bugfixes [`b5fc5ee`](https://github.com/julianneswinoga/tracex_parser/commit/b5fc5ee37593753dcc7cd2e8221e1e3e42d68ba5)

#### [2.3.0](https://github.com/julianneswinoga/tracex_parser/compare/2.2.0...2.3.0)

> 29 July 2023

- Fix event sorting (it's not by timestamp :/) [`551a05b`](https://github.com/julianneswinoga/tracex_parser/commit/551a05b7f447498f2c455146efc8bf6e08ddce77)
- Mask time stamp with timer valid mask [`03284a8`](https://github.com/julianneswinoga/tracex_parser/commit/03284a88e5d311d54d8410a7be89ba685b5e2e94)
- Add tests comparing Microsoft Store app output to our own parsing
- Add Initialization state to thread name conversion [`715b9d4`](https://github.com/julianneswinoga/tracex_parser/commit/715b9d48640fcd3fda6adf9ba1da72f32339c5b3)
- Change typing star import to explicit imports [`9f1c4c8`](https://github.com/julianneswinoga/tracex_parser/commit/9f1c4c86aef95ce78d8dc46d837763892eba571d)
- Generalize histogram string padding [`c4bfb5a`](https://github.com/julianneswinoga/tracex_parser/commit/c4bfb5a6f83f7eb5dc716b4df6ae58a7aae66f3c)

#### [2.2.0](https://github.com/julianneswinoga/tracex_parser/compare/2.1.0...2.2.0)

> 20 May 2023

- Update `poetry.lock` [`3b62367`](https://github.com/julianneswinoga/tracex_parser/commit/3b62367fe8423a462ef4b5e0f4045dc7feaeb374)
- Put `pool_ptr` into `CommonArg` [`d1308a6`](https://github.com/julianneswinoga/tracex_parser/commit/d1308a60387292b277b270d648785a56b46987ad)
- Add `BlockPoolCreate`, `BlockPoolDelete`, `BlockPoolInfo`, `BlockPoolPerformanceInfo`, `BlockPoolPerformanceSystemInfo`, `BlockPoolPrioritize` events [`0901f73`](https://github.com/julianneswinoga/tracex_parser/commit/0901f739f5ef4c9303a72817a6b93984f08bffd2)
- CI work around broken urllib3 dependency from poetry 1.1.15 [`4825189`](https://github.com/julianneswinoga/tracex_parser/commit/482518904c82b9f0a448a7abc338759b11540952)

#### [2.1.0](https://github.com/julianneswinoga/tracex_parser/compare/2.0.0...2.1.0)

> 10 March 2023

- Moved README.md documentation to sphinx docs [`d00855f`](https://github.com/julianneswinoga/tracex_parser/commit/d00855f34a0e6ee224b0c1ab3e92b4f5081e2bf8)
- Removed unneeded build_and_upload.sh scripts [`5800ae5`](https://github.com/julianneswinoga/tracex_parser/commit/5800ae5fb1a46332f419227f1b8b2ea922a79212)
- Added integration test, first real test [`1f0363c`](https://github.com/julianneswinoga/tracex_parser/commit/1f0363c25251127e7fab159c3637e7972f76f360)
- Add --color option to file_parser.py to force color output [`ce98e98`](https://github.com/julianneswinoga/tracex_parser/commit/ce98e98c5993ec654138c76a9445e16197e799c4)
- Fix docs build [`b15f529`](https://github.com/julianneswinoga/tracex_parser/commit/b15f529fb1a8e3851dea39eca06669b1d1fddfc3)

#### 2.0.0

> 10 September 2022

- Initial release with new build system
