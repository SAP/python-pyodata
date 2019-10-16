# How to contribute to PyOData

## **Did you find a bug?**

* Create a pull request for simple problems.

* Otherwise open a new issue with steps to reproduce.

## **Did you write a patch?**

* Before contributing, please, make yourself familiar with git. You can [try
  git online](https://try.github.io/). Things would be easier for all of us if
  you do your changes on a branch. Use a single commit for every logical
  reviewable change, without unrelated modifications (that will help us if need
  to revert a particular commit). Please avoid adding commits fixing your
  previous commits, do amend or rebase instead.

* Every Pull Request must contain test or a good justification why
  the test part is not included.

* If you believe that it is not necessary to add a test because there is
  already a test going through the statements you have modified, you are probably
  wrong because you either added something new and it should be tested or you fixed
  a bug which was not detected by the test and hence the test must be enhanced
  (ideally, you fist fix the test to reproduce the bug and then you fix the bug).

* Link commits to issues via referencing issue numbers: https://help.github.com/en/articles/closing-issues-using-keywords

* Every commit must have either comprehensive commit message saying what is being
  changed and why or a link (an issue number on Github) to a bug report where
  this information is available. It is also useful to include notes about
  negative decisions - i.e. why you decided to not do particular things. Please
  bare in mind that other developers might not understand what the original
  problem was.

* Try to follow the seven rules when writing commit messages: https://chris.beams.io/posts/git-commit/

* If you are not sure how to write a good commit message, go through
  the project history to find some inspiration.

* Update [CHANGELOG.md](CHANGELOG.md) (Unreleased section)

## **Did you fix whitespace, format code, or make a purely cosmetic patch?**

Changes that are cosmetic in nature and do not add anything substantial to the
stability, functionality, or testability of PyOData will generally not be
accepted.
