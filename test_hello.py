from hello import hello, main


def test_hello():
    assert hello() == "Hello, World!"


def test_main(capsys):
    main()
    captured = capsys.readouterr()
    assert captured.out == "Hello, World!\n"
